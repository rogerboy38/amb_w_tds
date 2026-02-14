// Container Barrels Dashboard JavaScript
frappe.pages['barrels'].on_page_load = function(wrapper) {
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
        method: 'amb_w_tds.amb_w_tds.page.barrels.barrels.get_dashboard_data',
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
    
    // Generate alerts HTML if any
    let alerts_html = '';
    if (data.alerts && data.alerts.length > 0) {
        alerts_html = `
            <div class="dashboard-alerts">
                ${data.alerts.map(alert => `
                    <div class="alert alert-${alert.type}">
                        ${alert.message}
                    </div>
                `).join('')}
            </div>
        `;
    }

    let dashboard_html = `
        <div class="dashboard-container">
            <div class="dashboard-header">
                <h2>Container Barrels Dashboard</h2>
                <button class="btn btn-primary btn-sm refresh-btn">
                    <i class="fa fa-refresh"></i> Refresh
                </button>
            </div>
            
            ${alerts_html}
            
            <div class="dashboard-stats">
                <div class="stat-card">
                    <div class="stat-icon">📦</div>
                    <h3>Total Barrels</h3>
                    <div class="stat-value">${data.total_barrels || 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">⚡</div>
                    <h3>Active Barrels</h3>
                    <div class="stat-value">${data.active_containers || 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🏷️</div>
                    <h3>Packaging Types</h3>
                    <div class="stat-value">${data.packaging_types ? data.packaging_types.length : 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📋</div>
                    <h3>Batches</h3>
                    <div class="stat-value">${data.batch_distribution ? data.batch_distribution.length : 0}</div>
                </div>
            </div>
            
            <div class="dashboard-content">
                ${data.html || '<div class="no-data"><p>No container data available</p></div>'}
            </div>
            
            <!-- Additional Data Sections -->
            <div class="additional-sections">
                ${render_packaging_types(data.packaging_types)}
                ${render_batch_distribution(data.batch_distribution)}
            </div>
        </div>
    `;
    
    $container.append(dashboard_html);
    
    // Add refresh button event
    $container.find('.refresh-btn').on('click', function() {
        $(this).find('i').addClass('fa-spin');
        load_container_dashboard_data(wrapper);
        setTimeout(() => {
            $(this).find('i').removeClass('fa-spin');
        }, 1000);
    });
    
    add_container_dashboard_css();
}

function render_packaging_types(packaging_types) {
    if (!packaging_types || packaging_types.length === 0) return '';
    
    return `
        <div class="data-section">
            <h4>📊 Packaging Types Distribution</h4>
            <div class="packaging-grid">
                ${packaging_types.map(pkg => `
                    <div class="packaging-item">
                        <div class="packaging-header">
                            <span class="packaging-type">${pkg.packaging_type}</span>
                            <span class="packaging-count">${pkg.count} barrels</span>
                        </div>
                        <div class="packaging-details">
                            Avg Weight: ${pkg.avg_weight || 0} kg
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function render_batch_distribution(batch_distribution) {
    if (!batch_distribution || batch_distribution.length === 0) return '';
    
    return `
        <div class="data-section">
            <h4>🏷️ Batch Distribution</h4>
            <div class="batch-table">
                <div class="batch-header">
                    <span>Batch</span>
                    <span>Barrels</span>
                    <span>Total Weight</span>
                    <span>Validated</span>
                </div>
                ${batch_distribution.map(batch => `
                    <div class="batch-row">
                        <span class="batch-name">${batch.batch}</span>
                        <span class="batch-count">${batch.barrel_count}</span>
                        <span class="batch-weight">${batch.total_weight || 0} kg</span>
                        <span class="batch-validated">${batch.validated_count}/${batch.barrel_count}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function add_container_dashboard_css() {
    if (!$('#container-barrels-dashboard-css').length) {
        $('head').append(`
            <style id="container-barrels-dashboard-css">
                .container-barrels-dashboard-container {
                    padding: 20px;
                    background: #f5f7fa;
                    min-height: 100vh;
                }
                
                .dashboard-container {
                    max-width: 1400px;
                    margin: 0 auto;
                }
                
                .dashboard-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 25px;
                    padding: 25px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    border-left: 5px solid #2e3a59;
                }
                
                .dashboard-header h2 {
                    margin: 0;
                    color: #2e3a59;
                    font-size: 24px;
                    font-weight: 600;
                }
                
                .refresh-btn {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .dashboard-alerts {
                    margin-bottom: 25px;
                }
                
                .dashboard-alerts .alert {
                    margin-bottom: 10px;
                    border-radius: 8px;
                    border: none;
                }
                
                .dashboard-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                
                .stat-card {
                    background: white;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    text-align: center;
                    transition: transform 0.2s ease, box-shadow 0.2s ease;
                    border-top: 4px solid #2e3a59;
                }
                
                .stat-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                }
                
                .stat-icon {
                    font-size: 32px;
                    margin-bottom: 10px;
                }
                
                .stat-card h3 {
                    margin: 0 0 10px 0;
                    font-size: 14px;
                    color: #6b7280;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .stat-value {
                    font-size: 36px;
                    font-weight: bold;
                    color: #2e3a59;
                }
                
                .dashboard-content {
                    background: white;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    margin-bottom: 25px;
                }
                
                .no-data {
                    text-align: center;
                    padding: 40px;
                    color: #6b7280;
                }
                
                .no-data p {
                    margin: 0;
                    font-size: 16px;
                }
                
                /* Dashboard Content Grid */
                .dashboard-content-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 25px;
                }
                
                .content-section {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    border-left: 4px solid #007bff;
                }
                
                .content-section.full-width {
                    grid-column: 1 / -1;
                }
                
                .content-section h4 {
                    margin: 0 0 15px 0;
                    color: #2e3a59;
                    font-size: 16px;
                    font-weight: 600;
                }
                
                /* Status List */
                .status-list .status-item {
                    display: flex;
                    align-items: center;
                    margin: 10px 0;
                    padding: 12px;
                    background: white;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                    transition: background-color 0.2s ease;
                }
                
                .status-list .status-item:hover {
                    background: #f8f9fa;
                }
                
                .status-badge {
                    width: 14px;
                    height: 14px;
                    border-radius: 50%;
                    margin-right: 12px;
                    flex-shrink: 0;
                }
                
                .status-new { background: #28a745; }
                .status-available { background: #17a2b8; }
                .status-in-use { background: #ffc107; }
                .status-empty { background: #6c757d; }
                .status-completed { background: #6f42c1; }
                .status-no-status { background: #6c757d; }
                
                /* Activities List */
                .activities-list .activity-item {
                    background: white;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 8px;
                    border-left: 4px solid #007bff;
                    border: 1px solid #e9ecef;
                    transition: transform 0.2s ease;
                }
                
                .activities-list .activity-item:hover {
                    transform: translateX(5px);
                }
                
                .activity-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }
                
                .activity-header strong {
                    color: #2e3a59;
                    font-size: 14px;
                }
                
                .activity-details {
                    color: #6c757d;
                    font-size: 13px;
                    margin-bottom: 8px;
                }
                
                .activities-list small {
                    color: #8d99a6;
                    font-size: 12px;
                }
                
                /* Quick Stats */
                .quick-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 15px;
                }
                
                .quick-stat {
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    border: 1px solid #e9ecef;
                    transition: transform 0.2s ease;
                }
                
                .quick-stat:hover {
                    transform: translateY(-2px);
                }
                
                .stat-label {
                    display: block;
                    font-size: 12px;
                    color: #6c757d;
                    margin-bottom: 8px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .stat-value {
                    display: block;
                    font-size: 20px;
                    font-weight: bold;
                    color: #2e3a59;
                }
                
                /* Additional Sections */
                .additional-sections {
                    display: grid;
                    gap: 25px;
                }
                
                .data-section {
                    background: white;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                
                .data-section h4 {
                    margin: 0 0 20px 0;
                    color: #2e3a59;
                    font-size: 18px;
                    font-weight: 600;
                    border-bottom: 2px solid #f1f3f4;
                    padding-bottom: 10px;
                }
                
                /* Packaging Grid */
                .packaging-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                }
                
                .packaging-item {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #17a2b8;
                }
                
                .packaging-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }
                
                .packaging-type {
                    font-weight: bold;
                    color: #2e3a59;
                }
                
                .packaging-count {
                    background: #17a2b8;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                }
                
                .packaging-details {
                    color: #6c757d;
                    font-size: 13px;
                }
                
                /* Batch Table */
                .batch-table {
                    display: grid;
                    gap: 1px;
                    background: #e9ecef;
                    border-radius: 8px;
                    overflow: hidden;
                }
                
                .batch-header, .batch-row {
                    display: grid;
                    grid-template-columns: 2fr 1fr 1fr 1fr;
                    gap: 1px;
                }
                
                .batch-header {
                    background: #2e3a59;
                    color: white;
                    font-weight: 600;
                    text-transform: uppercase;
                    font-size: 12px;
                    letter-spacing: 0.5px;
                }
                
                .batch-header span, .batch-row span {
                    padding: 15px;
                    background: white;
                    display: flex;
                    align-items: center;
                }
                
                .batch-header span {
                    background: #2e3a59;
                }
                
                .batch-row:hover span {
                    background: #f8f9fa;
                }
                
                .batch-name {
                    font-weight: 500;
                    color: #2e3a59;
                }
                
                .batch-count, .batch-weight, .batch-validated {
                    justify-content: center;
                    text-align: center;
                }
                
                /* Responsive Design */
                @media (max-width: 768px) {
                    .container-barrels-dashboard-container {
                        padding: 15px;
                    }
                    
                    .dashboard-header {
                        flex-direction: column;
                        gap: 15px;
                        text-align: center;
                    }
                    
                    .dashboard-stats {
                        grid-template-columns: 1fr;
                    }
                    
                    .dashboard-content-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .quick-stats {
                        grid-template-columns: 1fr;
                    }
                    
                    .packaging-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .batch-header, .batch-row {
                        grid-template-columns: 1fr;
                        text-align: center;
                    }
                    
                    .batch-header span, .batch-row span {
                        justify-content: center;
                    }
                }
            </style>
        `);
    }
}
