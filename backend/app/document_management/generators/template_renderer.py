import jinja2
from typing import Dict, Any
from datetime import datetime

class TemplateRenderer:
    @staticmethod
    def render(template_content: str, data: Dict[str, Any]) -> str:
        """
        Render Jinja2 template with data.
        """
        # Create environment with some default filters
        env = jinja2.Environment(autoescape=True)

        # Add common filters/functions
        env.globals.update({
            "now": datetime.utcnow,
            "format_date": lambda d, fmt="%Y-%m-%d": d.strftime(fmt) if d else "",
        })

        template = env.from_string(template_content)
        return template.render(**data)
