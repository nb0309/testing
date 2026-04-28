class AccessibilityClassifier:
    def __init__(self):
        pass

    def classify_announcement(self, role: str, name: str, html_snippet: str) -> dict:
        """
        Categorizes an accessibility node against WCAG 2.1 criteria.
        Returns passed and failed WCAG rules.
        """
        violations = []
        passes = []
        is_accessible = True
        
        role_lower = (role or "").lower()
        name_clean = (name or "").strip()
        has_name = len(name_clean) > 0 and name_clean.lower() not in ["unlabeled", "unlabelled", ""]
        
        # 1. WCAG 1.1.1 Non-text Content (Images, graphics)
        if role_lower in ["img", "image", "graphic", "figure"]:
            if not has_name:
                violations.append("WCAG 1.1.1: Non-text Content (Missing alt or name)")
                is_accessible = False
            else:
                passes.append("WCAG 1.1.1: Non-text Content")
                
        # 2. WCAG 4.1.2 Name, Role, Value (Interactive elements)
        interactive_roles = ["button", "link", "checkbox", "combobox", "slider", "textbox", "searchbox", "menuitem"]
        if role_lower in interactive_roles:
            if not has_name:
                violations.append("WCAG 4.1.2: Name, Role, Value (Interactive control missing name)")
                is_accessible = False
            else:
                passes.append("WCAG 4.1.2: Name, Role, Value")
                
        # 3. WCAG 2.4.4 Link Purpose
        if role_lower == "link":
            if not has_name:
                violations.append("WCAG 2.4.4: Link Purpose (In Context)")
                is_accessible = False
            elif name_clean.lower() in ["click here", "read more", "more", "link"]:
                violations.append("WCAG 2.4.4: Link Purpose (Ambiguous link text)")
                is_accessible = False
            else:
                passes.append("WCAG 2.4.4: Link Purpose")
                
        # 4. WCAG 1.3.1 Info and Relationships (Headings, Tables, Lists)
        structural_roles = ["heading", "table", "list", "listitem"]
        if role_lower in structural_roles:
            if not has_name and role_lower == "heading":
                violations.append("WCAG 1.3.1: Info and Relationships (Empty heading)")
                is_accessible = False
            else:
                passes.append("WCAG 1.3.1: Info and Relationships")
                
        # Heuristics derived purely from raw HTML smell
        if html_snippet:
            html_lower = html_snippet.lower()
            if "onclick=" in html_lower and role_lower not in ["button", "link", "menuitem"]:
                violations.append("WCAG 4.1.2: Name, Role, Value (Clickable element without interactive role)")
                is_accessible = False

        return {
            "is_accessible": is_accessible,
            "wcag_violations": ", ".join(violations) if violations else "None",
            "wcag_passes": ", ".join(passes) if passes else "None"
        }
