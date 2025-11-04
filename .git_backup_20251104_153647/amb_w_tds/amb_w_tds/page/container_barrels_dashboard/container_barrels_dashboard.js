// Container Barrels Dashboard JavaScript
frappe.pages['container_barrels_dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Container Barrels Dashboard',
        single_column: true
    });

    $(wrapper).find('.layout-main-section').addClass('container-barrels-dashboard-container');
    
    load_container_dashboard_data(wrapper);
};

function load_container_dashboard_data(wrapper) {
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.page.container_barrels_dashboard.container_barrels_dashboard.get_dashboard_data',
        callback: function(r) {
            if (r.message) {
                render_container_dashboard(wrapper, r.message);
            }
        },
        error: function(err) {
            console.error('Error loading container dashboard data:', err);
            frappe.msgprint(__('Error loading container dashboard data'));
        }
    });
}

function render_container_dashboard(wrapper, data) {
    let $container = $(wrapper).find('.container-barrels-dashboard-container');
    $container.empty();
    
    let dashboard_html = `
        <div class="dashboard-container">
            <div class="dashboard-header">
                <h2>Container Barrels Dashboard</h2>
                <button class="btn btn-primary btn-sm refresh-btn">Refresh</button>
            </div>
            <div class="dashboard-stats">
                <div class="stat-card">
                    <h3>Total Containers</h3>
                    <div class="stat-value">${data.total_containers || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>Active Containers</h3>
                    <div class="stat-value">${data.active_containers || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>Total Barrels</h3>
                    <div class="stat-value">${data.total_barrels || 0}</div>
                </div>
            </div>
            <div class="dashboard-content">
                ${data.html || '<p>No container data available</p>'}
            </div>
        </div>
    `;
    
    $container.append(dashboard_html);
    
    $container.find('.refresh-btn').on('click', function() {
        load_container_dashboard_data(wrapper);
    });
    
    add_container_dashboard_css();
}

function add_container_dashboard_css() {
    if (!$('#container-barrels-dashboard-css').length) {
        $('head').append(`
            <style id="container-barrels-dashboard-css">
                .container-barrels-dashboard-container {
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
