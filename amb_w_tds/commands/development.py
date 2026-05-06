import frappe
from frappe.commands import pass_context

@click.command('list-doctypes')
@click.argument('app')
@pass_context
def list_doctypes(context, app):
    """List all doctypes in a specific app"""
    docs = frappe.get_list('DocType', filters={'module': app}, pluck='name')
    for doc in docs:
        click.echo(doc)
