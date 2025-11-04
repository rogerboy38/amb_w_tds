// Copyright (c) 2025, SPC Team and contributors
// Container Barrels Dashboard - Frontend

frappe.pages['container-barrels-dashboard'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Container Barrels Dashboard',
        single_column: true
    });
    
    page.add_inner_button(__('Refresh'), function() {
        dashboard.load_data();
    }).css({'font-weight': 'bold'});
    
    page.add_inner_button(__('View All Barrels'), function() {
        frappe.set_route('List', 'Batch AMB');
    });
    
    let dashboard = new ContainerBarrelsDashboard(page);
};

class ContainerBarrelsDashboard {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.setup();
    }
    
    setup() {
        this.wrapper.html(`
            <div class="container-barrels-dashboard">
                <div id="alerts-section" class="dashboard-section"></div>
                
                <div id="summary-cards" class="dashboard-section">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="summary-card" data-stat="total" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                                <div class="stat-icon">📦</div>
                                <div class="stat-value" id="total-barrels">--</div>
                                <div class="stat-label">Total Barrels</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="summary-card" data-stat="in-use" style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);">
                                <div class="stat-icon">✅</div>
                                <div class="stat-value" id="in-use-barrels">--</div>
                                <div class="stat-label">In Use</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="summary-card" data-stat="available" style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);">
                                <div class="stat-icon">🔄</div>
                                <div class="stat-value" id="available-barrels">--</div>
                                <div class="stat-label">Available</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="summary-card" data-stat="maintenance" style="background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);">
                                <div class="stat-icon">🔧</div>
                                <div class="stat-value" id="maintenance-barrels">--</div>
                                <div class="stat-label">Maintenance</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div id="usage-section" class="dashboard-section">
                    <h3>Usage Statistics</h3>
                    <div class="usage-stats">
                        <div class="usage-item">
                            <span class="usage-label">Average Usage:</span>
                            <span class="usage-value" id="avg-usage">--</span>
                        </div>
                        <div class="usage-item">
                            <span class="usage-label">Total Fill Cycles:</span>
                            <span class="usage-value" id="total-fills">--</span>
                        </div>
                        <div class="usage-item">
                            <span class="usage-label">Total Empty Cycles:</span>
                            <span class="usage-value" id="total-empties">--</span>
                        </div>
                        <div class="usage-item">
                            <span class="usage-label">Avg Net Weight:</span>
                            <span class="usage-value" id="avg-weight">-- kg</span>
                        </div>
                    </div>
                </div>
                
                <div class="row dashboard-section">
                    <div class="col-md-6">
                        <div class="chart-container">
                            <h4>Status Distribution</h4>
                            <div id="status-chart" style="height: 300px;"></div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="chart-container">
                            <h4>Location Distribution</h4>
                            <div id="location-chart" style="height: 300px;"></div>
                        </div>
                    </div>
                </div>
                
                <div class="row dashboard-section">
                    <div class="col-md-6">
                        <div class="chart-container">
                            <h4>Usage Analysis</h4>
                            <div id="usage-chart" style="height: 300px;"></div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="chart-container">
                            <h4>Packaging Type Distribution</h4>
                            <div id="packaging-chart" style="height: 300px;"></div>
                        </div>
                    </div>
                </div>
                
                <div class="row dashboard-section">
                    <div class="col-md-12">
                        <div class="chart-container">
                            <h4>Top Batches by Barrel Count</h4>
                            <div id="batch-chart" style="height: 300px;"></div>
                        </div>
                    </div>
                </div>
                
                <div id="recent-activities" class="dashboard-section">
                    <h3>Recent Activities</h3>
                    <div id="activities-list"></div>
                </div>
            </div>
        `);
        
        this.add_custom_styles();
        this.load_data();
        this.setup_auto_refresh();
    }
    
    add_custom_styles() {
        const style = `
            <style>
                .container-barrels-dashboard {
                    padding: 20px;
                }
                
                .dashboard-section {
                    margin-bottom: 30px;
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                
                .summary-card {
                    color: white;
                    padding: 25px;
                    border-radius: 10px;
                    text-align: center;
                    cursor: pointer;
                    transition: transform 0.2s;
                    margin-bottom: 15px;
                }
                
                .summary-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                }
                
                .stat-icon {
                    font-size: 48px;
                    margin-bottom: 10px;
                }
                
                .stat-value {
                    font-size: 36px;
                    font-weight: bold;
                    margin: 10px 0;
                }
                
                .stat-label {
                    font-size: 14px;
                    opacity: 0.9;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                
                .usage-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }
                
                .usage-item {
                    padding: 15px;
                    background: #f5f5f5;
                    border-radius: 5px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .usage-label {
                    font-weight: 600;
                    color: #666;
                }
                
                .usage-value {
                    font-size: 20px;
                    font-weight: bold;
                    color: #333;
                }
                
                .chart-container {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                
                .chart-container h4 {
                    margin-bottom: 15px;
                    color: #333;
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 10px;
                }
                
                .alert-item {
                    padding: 15px;
                    margin-bottom: 10px;
                    border-radius: 5px;
                    border-left: 4px solid;
                }
                
                .alert-item.warning {
                    background: #fff3cd;
                    border-color: #ff9800;
                    color: #856404;
                }
                
                .alert-item.info {
                    background: #d1ecf1;
                    border-color: #2196F3;
                    color: #0c5460;
                }
                
                .activity-item {
                    padding: 15px;
                    border-bottom: 1px solid #eee;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    transition: background 0.2s;
                    cursor: pointer;
                }
                
                .activity-item:hover {
                    background: #f5f5f5;
                }
                
                .activity-item:last-child {
                    border-bottom: none;
                }
            </style>
        `;
        
        if (!$('#container-barrels-dashboard-styles').length) {
            $('head').append(style);
        }
    }
    
    load_data() {
        frappe.call({
            method: 'amb_w_tds.amb_w_tds.page.container_barrels_dashboard.container_barrels_dashboard.get_dashboard_data',
            callback: (r) => {
                if (r.message) {
                    this.render_data(r.message);
                }
            }
        });
    }
    
    render_data(data) {
        this.render_alerts(data.alerts);
        
        $('#total-barrels').text(data.summary.total_barrels);
        $('#in-use-barrels').text(data.summary.in_use_barrels);
        $('#available-barrels').text(data.summary.available_barrels);
        $('#maintenance-barrels').text(data.summary.maintenance_barrels);
        
        $('#avg-usage').text(data.summary.avg_usage);
        $('#total-fills').text(data.summary.total_fill_cycles);
        $('#total-empties').text(data.summary.total_empty_cycles);
        $('#avg-weight').text(data.summary.avg_net_weight + ' kg');
        
        this.render_status_chart(data.status_distribution);
        this.render_location_chart(data.location_distribution);
        this.render_usage_chart(data.usage_analysis);
        this.render_packaging_chart(data.packaging_types);
        this.render_batch_chart(data.batch_distribution);
        
        this.render_activities(data.recent_activities);
        
        this.add_card_click_handlers();
    }
    
    render_alerts(alerts) {
        const alerts_html = alerts.map(alert => `
            <div class="alert-item ${alert.type}">
                <span>${alert.message}</span>
            </div>
        `).join('');
        
        $('#alerts-section').html(alerts_html || '<p style="color: #666;">✅ No alerts - All systems normal!</p>');
    }
    
    render_status_chart(data) {
        if (data.length === 0) return;
        
        const chart_data = {
            labels: data.map(d => d.status),
            datasets: [{
                values: data.map(d => d.count)
            }]
        };
        
        new frappe.Chart("#status-chart", {
            data: chart_data,
            type: 'pie',
            height: 300,
            colors: ['#4CAF50', '#2196F3', '#ff9800', '#f44336', '#9c27b0']
        });
    }
    
    render_location_chart(data) {
        if (data.length === 0) return;
        
        const chart_data = {
            labels: data.map(d => d.location),
            datasets: [{
                name: 'Barrel Count',
                values: data.map(d => d.count)
            }]
        };
        
        new frappe.Chart("#location-chart", {
            data: chart_data,
            type: 'bar',
            height: 300,
            colors: ['#2196F3']
        });
    }
    
    render_usage_chart(data) {
        if (data.length === 0) return;
        
        const chart_data = {
            labels: data.map(d => d.usage_range),
            datasets: [{
                name: 'Barrels',
                values: data.map(d => d.count)
            }]
        };
        
        new frappe.Chart("#usage-chart", {
            data: chart_data,
            type: 'bar',
            height: 300,
            colors: ['#4CAF50']
        });
    }
    
    render_packaging_chart(data) {
        if (data.length === 0) return;
        
        const chart_data = {
            labels: data.map(d => d.packaging_type),
            datasets: [{
                values: data.map(d => d.count)
            }]
        };
        
        new frappe.Chart("#packaging-chart", {
            data: chart_data,
            type: 'donut',
            height: 300,
            colors: ['#9c27b0', '#ff9800', '#4CAF50', '#2196F3']
        });
    }
    
    render_batch_chart(data) {
        if (data.length === 0) return;
        
        const chart_data = {
            labels: data.map(d => d.batch),
            datasets: [{
                name: 'Barrels per Batch',
                values: data.map(d => d.barrel_count)
            }]
        };
        
        new frappe.Chart("#batch-chart", {
            data: chart_data,
            type: 'bar',
            height: 300,
            colors: ['#667eea']
        });
    }
    
    render_activities(activities) {
        const activities_html = activities.map(activity => `
            <div class="activity-item" onclick="frappe.set_route('Form', 'Batch AMB', '${activity.parent}')">
                <div>
                    <strong>${activity.barrel_serial_number}</strong>
                    <span class="badge badge-primary">${activity.status}</span>
                    <div style="font-size: 12px; color: #666;">
                        Batch: ${activity.parent} | Location: ${activity.current_warehouse || 'N/A'}
                    </div>
                </div>
                <div style="text-align: right; font-size: 12px; color: #888;">
                    ${moment(activity.modified).fromNow()}
                    <div>by ${activity.modified_by}</div>
                </div>
            </div>
        `).join('');
        
        $('#activities-list').html(activities_html);
    }
    
    add_card_click_handlers() {
        $('.summary-card').click(function() {
            frappe.set_route('List', 'Batch AMB');
        });
    }
    
    setup_auto_refresh() {
        setInterval(() => {
            this.load_data();
        }, 30000);
    }
}
