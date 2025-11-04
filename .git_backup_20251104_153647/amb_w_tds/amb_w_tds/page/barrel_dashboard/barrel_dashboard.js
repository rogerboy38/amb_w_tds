// Barrel Management Dashboard JavaScript
frappe.pages['barrel_dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Barrel Dashboard',
        single_column: true
    });

    $(wrapper).find('.layout-main-section').addClass('barrel-dashboard-container');
    
    load_dashboard_data(wrapper);
};

function load_dashboard_data(wrapper) {
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.page.barrel_dashboard.barrel_dashboard.get_dashboard_data',
        callback: function(r) {
            if (r.message) {
                render_dashboard(wrapper, r.message);
            }
        },
        error: function(err) {
            console.error('Error loading dashboard data:', err);
            frappe.msgprint(__('Error loading dashboard data'));
        }
    });
}

function render_dashboard(wrapper, data) {
    let $container = $(wrapper).find('.barrel-dashboard-container');
    $container.empty();
    
    let dashboard_html = `
        <div class="dashboard-container">
            <div class="dashboard-header">
                <h2>Barrel Management Dashboard</h2>
                <button class="btn btn-primary btn-sm refresh-btn">Refresh</button>
            </div>
            <div class="dashboard-stats">
                <div class="stat-card">
                    <h3>Total Barrels</h3>
                    <div class="stat-value">${data.total_barrels || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>Active Barrels</h3>
                    <div class="stat-value">${data.active_barrels || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>Available Barrels</h3>
                    <div class="stat-value">${data.available_barrels || 0}</div>
                </div>
            </div>
            <div class="dashboard-content">
                ${data.html || '<p>No data available</p>'}
            </div>
        </div>
    `;
    
    $container.append(dashboard_html);
    
    $container.find('.refresh-btn').on('click', function() {
        load_dashboard_data(wrapper);
    });
    
    add_dashboard_css();
}

function add_dashboard_css() {
    if (!$('#barrel-dashboard-css').length) {
        $('head').append(`
            <style id="barrel-dashboard-css">
                .barrel-dashboard-container {
                    padding: 20px;
                    background: #f5f7fa;
                }
                .dashboard-container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                .dashboard-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 30px;
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .dashboard-header h2 {
                    margin: 0;
                    color: #2e3a59;
                }
                .dashboard-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .stat-card {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                }
                .stat-card h3 {
                    margin: 0 0 10px 0;
                    font-size: 14px;
                    color: #6b7280;
                    text-transform: uppercase;
                }
                .stat-value {
                    font-size: 32px;
                    font-weight: bold;
                    color: #2e3a59;
                }
                .dashboard-content {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
            </style>
        `);
    }
}
