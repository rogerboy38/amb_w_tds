# amb_w_tds package
__version__ = "9.0.0"


#from . import __version__ as version

app_name = "amb_w_tds"
app_title = "AMB W TDS"
app_publisher = "Your Company"
app_description = "Barrel Management System"
app_icon = "fa fa-tint"
app_color = "#3498db"
app_email = "your-email@example.com"
app_license = "MIT"

# Include pages in website route
website_route_rules = [
    {"from_route": "/barrel_dashboard", "to_route": "barrel_dashboard"},
    {"from_route": "/container_barrels_dashboard", "to_route": "container_barrels_dashboard"}
]

# After install setup
after_install = "amb_w_tds.setup.setup_pages.after_install"

# Export modules for scheduler events
from . import migration
from .api import agent, audit, quotation_amb, validate
from .agent import performance
from .raven import utils

