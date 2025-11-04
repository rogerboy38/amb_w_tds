// Copyright (c) 2025, SPC Team and contributors
// Barrel Management Dashboard - Frontend

frappe.pages['barrel-dashboard'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Barrel Management Dashboard',
        single_column: true
    });
    
    page.add_inner_button(__('Refresh'), function() {
        load_dashboard_data(page);
    }).css({'font-weight': 'bold'});
    
    page.add_inner_button(__('View All Barrels'), function() {
        frappe.set_route('List', 'Barrel');
    });
    
    new BarrelDashboard(page);
};

class BarrelDashboard {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.setup();
    }
    
    setup() {
        this.wrapper.html(`
            <div class="barrel-dashboard">
                <div id="alerts-section" class="dashboard-section"></div>
                
                <div id="summary-cards" class="dashboard-section">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="summary-card" data-stat="total">
                                <div class="stat-icon">📦</div>
                                <div class="stat-value" id="total-barrels">--</div>
                                <div class="stat-label">Total Barrels</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="summary-card" data-stat="available">
                                <div class="stat-icon">✅</div>
                                <div class="stat-value" id="available-barrels">--</div>
                                <div class="stat-label">Available</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="summary-card" data-stat="in-use">
                                <div class="stat-icon">🔄</div>
                                <div class="stat-value" id="in-use-barrels">--</div>
                                <div class="stat-label">In Use</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="summary-card" data-stat="maintenance">
                                <div class="stat-icon">🔧</div>
                                <div class="stat-value" id="maintenance-barrels">--</div>
                                <div class="stat-label">Maintenance</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div id="capacity-section" class="dashboard-section">
                    <h3>Capacity Overview</h3>
                    <div class="capacity-stats">
                        <div class="capacity-item">
                            <span class="capacity-label">Total Capacity:</span>
                            <span class="capacity-value" id="total-capacity">-- gal</span>
                        </div>
                        <div class="capacity-item">
                            <span class="capacity-label">Filled:</span>
                            <span class="capacity-value" id="filled-volume">-- gal</span>
                        </div>
                        <div class="capacity-item">
                            <span class="capacity-label">Available:</span>
                            <span class="capacity-value" id="available-volume">-- gal</span>
                        </div>
                        <div class="capacity-item">
                            <span class="capacity-label">Utilization:</span>
                            <span class="capacity-value" id="capacity-utilization">--%</span>
                        </div>
                    </div>
                    <div id="capacity-chart" style="height: 200px; margin-top: 20px;"></div>
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
                            <h4>Fill Level Analysis</h4>
                            <div id="fill-level-chart" style="height: 300px;"></div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="chart-container">
                            <h4>Barrel Type Distribution</h4>
                            <div id="type-chart" style="height: 300px;"></div>
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
                .barrel-dashboard {
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
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                
                .summary-card[data-stat="available"] {
                    background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                }
                
                .summary-card[data-stat="in-use"] {
                    background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
                }
                
                .summary-card[data-stat="maintenance"] {
                    background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
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
                
                .capacity-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }
                
                .capacity-item {
                    padding: 15px;
                    background: #f5f5f5;
                    border-radius: 5px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .capacity-label {
                    font-weight: 600;
                    color: #666;
                }
                
                .capacity-value {
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
                
                .alert-item.danger {
                    background: #f8d7da;
                    border-color: #f44336;
                    color: #721c24;
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
        
        if (!$('#barrel-dashboard-styles').length) {
            $('head').append(style);
        }
    }
    
    load_data() {
        frappe.call({
            method: 'amb_w_tds.amb_w_tds.page.barrel_dashboard.barrel_dashboard.get_dashboard_data',
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
        $('#available-barrels').text(data.summary.available_barrels);
        $('#in-use-barrels').text(data.summary.in_use_barrels);
        $('#maintenance-barrels').text(data.summary.maintenance_barrels);
        
        $('#total-capacity').text(data.summary.total_capacity + ' gal');
        $('#filled-volume').text(data.summary.filled_volume + ' gal');
        $('#available-volume').text(data.summary.available_volume + ' gal');
        $('#capacity-utilization').text(data.summary.capacity_utilization + '%');
        
        this.render_status_chart(data.status_distribution);
        this.render_location_chart(data.location_distribution);
        this.render_fill_level_chart(data.fill_level_analysis);
        this.render_type_chart(data.barrel_types);
        this.render_capacity_chart(data.summary);
        
        this.render_activities(data.recent_activities);
        
        this.add_card_click_handlers();
    }
    
    render_alerts(alerts) {
        const alerts_html = alerts.map(alert => `
            <div class="alert-item ${alert.type}">
                <span>${alert.message}</span>
            </div>
        `).join('');
        
        $('#alerts-section').html(alerts_html || '<p style="color: #666;">No alerts at this time.</p>');
    }
    
    render_status_chart(data) {
        if (data.length === 0) return;
        
        const chart_data = {
            labels: data.map(d => d.current_status),
            datasets: [{
                values: data.map(d => d.count)
            }]
        };
        
        new frappe.Chart("#status-chart", {
            data: chart_data,
            type: 'pie',
            height: 300,
            colors: ['#4CAF50', '#2196F3', '#ff9800', '#f44336', '#9c27b0', '#ffeb3b']
        });
    }
    
    render_location_chart(data) {
        if (data.length === 0) return;
        
        const chart_data = {
            labels: data.map(d => d.current_location || 'Unknown'),
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
    
    render_fill_level_chart(data) {
        if (data.length === 0) return;
        
        const chart_data = {
            labels: data.map(d => d.fill_range),
            datasets: [{
                name: 'Barrels',
                values: data.map(d => d.count)
            }]
        };
        
        new frappe.Chart("#fill-level-chart", {
            data: chart_data,
            type: 'bar',
            height: 300,
            colors: ['#4CAF50']
        });
    }
    
    render_type_chart(data) {
        if (data.length === 0) return;
        
        const chart_data = {
            labels: data.map(d => d.barrel_type),
            datasets: [{
                values: data.map(d => d.count)
            }]
        };
        
        new frappe.Chart("#type-chart", {
            data: chart_data,
            type: 'donut',
            height: 300,
            colors: ['#9c27b0', '#ff9800', '#4CAF50', '#2196F3', '#f44336']
        });
    }
    
    render_capacity_chart(summary) {
        const chart_data = {
            labels: ['Filled', 'Available'],
            datasets: [{
                values: [summary.filled_volume, summary.available_volume]
            }]
        };
        
        new frappe.Chart("#capacity-chart", {
            data: chart_data,
            type: 'percentage',
            height: 200,
            colors: ['#2196F3', '#4CAF50']
        });
    }
    
    render_activities(activities) {
        const activities_html = activities.map(activity => `
            <div class="activity-item" onclick="frappe.set_route('Form', 'Barrel', '${activity.name}')">
                <div>
                    <strong>${activity.barrel_code}</strong>
                    <span class="badge badge-primary">${activity.current_status}</span>
                    <div style="font-size: 12px; color: #666;">
                        Location: ${activity.current_location || 'N/A'}
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
            const stat = $(this).data('stat');
            const filters = {
                'total': {},
                'available': {'current_status': 'Available'},
                'in-use': {'current_status': 'In Use'},
                'maintenance': {'current_status': 'Maintenance'}
            };
            
            frappe.route_options = filters[stat];
            frappe.set_route('List', 'Barrel');
        });
    }
    
    setup_auto_refresh() {
        setInterval(() => {
            this.load_data();
        }, 30000);
    }
}
