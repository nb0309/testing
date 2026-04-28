import json
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class NVDACapture:
    def __init__(self):
        pass

    def capture(self, url: str, mode: str = "browse") -> dict:
        """
        Runs Selenium for the given URL and mode ('browse' or 'interactive') 
        and returns the captured accessibility data imitating NVDA.
        """
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            # Give the page a moment to fully render and idle (simulating networkidle)
            time.sleep(2)

            # Enable DOM and fetch Accessibility Tree using Chrome DevTools Protocol
            driver.execute_cdp_cmd('DOM.enable', {})
            ax_tree = driver.execute_cdp_cmd('Accessibility.getFullAXTree', {})
            nodes = ax_tree.get('nodes', [])

            records = []
            index = 0

            if mode == 'browse':
                # --- BROWSE MODE (Simulating Virtual Cursor / Down Arrow) ---
                for node in nodes:
                    if node.get('ignored'): 
                        continue
                    
                    role = node.get('role', {}).get('value')
                    name = node.get('name', {}).get('value')

                    if role and name is not None and role not in ('RootWebArea', 'GenericContainer'):
                        announcement = f"{name or 'unlabeled'} {role}"
                        
                        properties = node.get('properties', [])
                        val_prop = next((p for p in properties if p.get('name') == 'value'), None)
                        if val_prop and val_prop.get('value') and val_prop['value'].get('value'):
                            announcement += f" {val_prop['value']['value']}"

                        # Fetch raw HTML snippet using backendDOMNodeId if available
                        html_snippet = None
                        backend_node_id = node.get('backendDOMNodeId')
                        if backend_node_id:
                            try:
                                resolved = driver.execute_cdp_cmd('DOM.resolveNode', {'backendNodeId': backend_node_id})
                                object_id = resolved.get('object', {}).get('objectId')
                                if object_id:
                                    outer = driver.execute_cdp_cmd('DOM.getOuterHTML', {'objectId': object_id})
                                    html_snippet = outer.get('outerHTML')
                                    if html_snippet and len(html_snippet) > 500:
                                        html_snippet = html_snippet[:500] + '...'
                            except Exception:
                                pass

                        records.append({
                            "index": index,
                            "role": role,
                            "name": name,
                            "html_snippet": html_snippet or "",
                            "announcement": announcement.strip()
                        })
                        index += 1

            elif mode == 'interactive':
                # --- INTERACTIVE MODE (Simulating Tab Key Navigation) ---
                # Clear focus first
                driver.execute_script("if (document.activeElement) document.activeElement.blur();")
                
                previous_focus_html = None
                consecutive_same_focus = 0
                tab_count = 0
                seen_htmls = set()

                actions = ActionChains(driver)

                while tab_count < 500:
                    actions.send_keys(Keys.TAB).perform()
                    tab_count += 1
                    
                    current_html = driver.execute_script("return document.activeElement !== document.body ? document.activeElement.outerHTML : null;")
                    
                    if not current_html or current_html == previous_focus_html or current_html in seen_htmls:
                        consecutive_same_focus += 1
                        # If we tab multiple times and focus doesn't change or we hit a cyclic trap, break out
                        if consecutive_same_focus > 5:
                            break
                    else:
                        consecutive_same_focus = 0
                        previous_focus_html = current_html
                        seen_htmls.add(current_html)

                        try:
                            # Get the CDP description of the newly active element
                            eval_res = driver.execute_cdp_cmd('Runtime.evaluate', {'expression': 'document.activeElement', 'returnByValue': False})
                            object_id = eval_res.get('result', {}).get('objectId')

                            if object_id:
                                desc = driver.execute_cdp_cmd('DOM.describeNode', {'objectId': object_id})
                                backend_node_id = desc.get('node', {}).get('backendNodeId')

                                # Find this element in the accessibility tree
                                ax_node = next((n for n in nodes if n.get('backendDOMNodeId') == backend_node_id), None)
                                
                                role = ax_node.get('role', {}).get('value') if ax_node and ax_node.get('role') else 'unknown'
                                name = ax_node.get('name', {}).get('value') if ax_node and ax_node.get('name') else None

                                announcement = f"{name or 'unlabeled'} {role}"

                                if ax_node and ax_node.get('properties'):
                                    val_prop = next((p for p in ax_node['properties'] if p.get('name') == 'value'), None)
                                    if val_prop and val_prop.get('value') and val_prop['value'].get('value'):
                                        announcement += f" {val_prop['value']['value']}"

                                snippet = current_html[:500] + '...' if len(current_html) > 500 else current_html

                                records.append({
                                    "index": index,
                                    "role": role,
                                    "name": name,
                                    "html_snippet": snippet,
                                    "announcement": announcement.strip()
                                })
                                index += 1
                        except Exception:
                            # Ignore unresolvable nodes
                            pass

            return {
                "url": url,
                "mode": mode,
                "success": True,
                "data": records
            }

        except Exception as e:
            return {
                "url": url,
                "mode": mode,
                "success": False,
                "error": str(e)
            }
        finally:
            if driver:
                driver.quit()
