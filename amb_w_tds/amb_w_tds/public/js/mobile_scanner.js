/**
 * Mobile Scanner Interface for Container Management
 * Touch-optimized interface for handheld scanners and mobile devices
 */

// Mobile Scanner Application
class MobileContainerScanner {
    constructor() {
        this.currentContainer = null;
        this.scanQueue = [];
        this.isOnline = navigator.onLine;
        this.currentPlant = null;
        this.settings = this.loadSettings();
        
        this.init();
        this.setupEventListeners();
        this.loadOfflineQueue();
    }
    
    init() {
        // Create mobile UI
        this.createMobileInterface();
        
        // Setup plant selection
        this.loadPlantOptions();
        
        // Setup keyboard shortcuts for scanner
        this.setupScannerShortcuts();
        
        // Check online status
        this.updateOnlineStatus();
    }
    
    createMobileInterface() {
        const container = document.getElementById('mobile-scanner-container') || document.createElement('div');
        container.id = 'mobile-scanner-container';
        container.className = 'mobile-scanner-app';
        
        container.innerHTML = `
            <div class="scanner-header">
                <h2>Container Scanner</h2>
                <div class="status-indicators">
                    <span id="online-status" class="status-indicator">●</span>
                    <span id="plant-indicator">${this.currentPlant || 'No Plant'}</span>
                    <span id="queue-count">Queue: 0</span>
                </div>
            </div>
            
            <div class="scanner-controls">
                <div class="plant-selector">
                    <label>Plant:</label>
                    <select id="plant-select">
                        <option value="">Select Plant</option>
                    </select>
                </div>
                
                <div class="scan-input-section">
                    <input 
                        type="text" 
                        id="barcode-input" 
                        placeholder="Scan or enter barcode"
                        class="barcode-input"
                        autocomplete="off"
                    >
                    <button id="manual-scan-btn" class="scan-btn">Scan</button>
                </div>
                
                <div class="quick-actions">
                    <button id="weight-entry-btn" class="action-btn">Weight Entry</button>
                    <button id="status-update-btn" class="action-btn">Update Status</button>
                    <button id="batch-assign-btn" class="action-btn">Assign Batch</button>
                </div>
            </div>
            
            <div class="current-container" id="current-container-display" style="display:none;">
                <h3>Current Container</h3>
                <div class="container-info">
                    <div class="info-row">
                        <span class="label">ID:</span>
                        <span id="container-id"></span>
                    </div>
                    <div class="info-row">
                        <span class="label">Type:</span>
                        <span id="container-type"></span>
                    </div>
                    <div class="info-row">
                        <span class="label">Status:</span>
                        <span id="container-status"></span>
                    </div>
                    <div class="info-row">
                        <span class="label">Weight:</span>
                        <span id="container-weight"></span>
                    </div>
                </div>
                
                <div class="container-actions">
                    <button id="clear-container" class="secondary-btn">Clear</button>
                    <button id="save-container" class="primary-btn">Save Changes</button>
                </div>
            </div>
            
            <div class="scan-history">
                <h3>Recent Scans <span id="sync-all-btn" class="sync-btn">⟳ Sync All</span></h3>
                <div id="scan-history-list"></div>
            </div>
            
            <div class="settings-panel" id="settings-panel" style="display:none;">
                <h3>Scanner Settings</h3>
                <div class="setting-item">
                    <label>
                        <input type="checkbox" id="auto-sync"> Auto Sync
                    </label>
                </div>
                <div class="setting-item">
                    <label>
                        <input type="checkbox" id="sound-enabled"> Sound Alerts
                    </label>
                </div>
                <div class="setting-item">
                    <label>Sync Interval (sec):</label>
                    <input type="number" id="sync-interval" value="30" min="10" max="300">
                </div>
            </div>
        `;
        
        if (!document.getElementById('mobile-scanner-container')) {
            document.body.appendChild(container);
        }
        
        // Apply mobile styles
        this.applyMobileStyles();
    }
    
    applyMobileStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .mobile-scanner-app {
                max-width: 100%;
                padding: 10px;
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                min-height: 100vh;
            }
            
            .scanner-header {
                background: #2196F3;
                color: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 15px;
            }
            
            .status-indicators {
                display: flex;
                justify-content: space-between;
                margin-top: 10px;
                font-size: 14px;
            }
            
            .status-indicator {
                font-size: 18px;
            }
            
            .status-indicator.online { color: #4CAF50; }
            .status-indicator.offline { color: #F44336; }
            
            .scanner-controls {
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .plant-selector {
                margin-bottom: 15px;
            }
            
            .plant-selector select {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 16px;
            }
            
            .scan-input-section {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
            }
            
            .barcode-input {
                flex: 1;
                padding: 12px;
                border: 2px solid #2196F3;
                border-radius: 4px;
                font-size: 18px;
            }
            
            .scan-btn, .action-btn, .primary-btn, .secondary-btn {
                padding: 12px 20px;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                cursor: pointer;
                transition: background 0.3s;
            }
            
            .scan-btn { background: #4CAF50; color: white; }
            .action-btn { background: #FF9800; color: white; margin: 5px; }
            .primary-btn { background: #2196F3; color: white; }
            .secondary-btn { background: #757575; color: white; }
            
            .quick-actions {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }
            
            .current-container {
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border-left: 4px solid #4CAF50;
            }
            
            .container-info {
                margin: 15px 0;
            }
            
            .info-row {
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #eee;
            }
            
            .label {
                font-weight: bold;
                color: #666;
            }
            
            .container-actions {
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }
            
            .scan-history {
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .scan-history h3 {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            
            .sync-btn {
                background: #FF9800;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }
            
            .history-item {
                padding: 10px;
                border: 1px solid #eee;
                border-radius: 4px;
                margin-bottom: 10px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .history-item.synced { border-left: 4px solid #4CAF50; }
            .history-item.pending { border-left: 4px solid #FF9800; }
            .history-item.error { border-left: 4px solid #F44336; }
            
            @media (max-width: 768px) {
                .mobile-scanner-app { padding: 5px; }
                .barcode-input { font-size: 16px; }
                .quick-actions { flex-direction: column; }
                .action-btn { width: 100%; }
            }
        `;
        
        if (!document.getElementById('mobile-scanner-styles')) {
            style.id = 'mobile-scanner-styles';
            document.head.appendChild(style);
        }
    }
    
    setupEventListeners() {
        // Barcode input
        const barcodeInput = document.getElementById('barcode-input');
        const scanBtn = document.getElementById('manual-scan-btn');
        
        barcodeInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.processScan(e.target.value);
                e.target.value = '';
            }
        });
        
        scanBtn.addEventListener('click', () => {
            this.processScan(barcodeInput.value);
            barcodeInput.value = '';
        });
        
        // Plant selection
        document.getElementById('plant-select').addEventListener('change', (e) => {
            this.currentPlant = e.target.value;
            this.saveSettings();
            this.updatePlantIndicator();
        });
        
        // Action buttons
        document.getElementById('weight-entry-btn').addEventListener('click', () => {
            this.openWeightDialog();
        });
        
        document.getElementById('status-update-btn').addEventListener('click', () => {
            this.openStatusDialog();
        });
        
        document.getElementById('batch-assign-btn').addEventListener('click', () => {
            this.openBatchDialog();
        });
        
        // Container actions
        document.getElementById('clear-container').addEventListener('click', () => {
            this.clearCurrentContainer();
        });
        
        document.getElementById('save-container').addEventListener('click', () => {
            this.saveCurrentContainer();
        });
        
        // Sync all button
        document.getElementById('sync-all-btn').addEventListener('click', () => {
            this.syncAllPending();
        });
        
        // Online/offline events
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateOnlineStatus();
            this.syncAllPending();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateOnlineStatus();
        });
    }
    
    setupScannerShortcuts() {
        document.addEventListener('keydown', (e) => {
            // F1: Focus barcode input
            if (e.key === 'F1') {
                e.preventDefault();
                document.getElementById('barcode-input').focus();
            }
            
            // F2: Weight entry
            if (e.key === 'F2') {
                e.preventDefault();
                this.openWeightDialog();
            }
            
            // F3: Status update
            if (e.key === 'F3') {
                e.preventDefault();
                this.openStatusDialog();
            }
            
            // ESC: Clear current container
            if (e.key === 'Escape') {
                this.clearCurrentContainer();
            }
        });
    }
    
    async loadPlantOptions() {
        try {
            const response = await frappe.call({
                method: 'amb_w_tds.api.plant_management.get_all_plants'
            });
            
            if (response.message && response.message.success) {
                const plantSelect = document.getElementById('plant-select');
                plantSelect.innerHTML = '<option value="">Select Plant</option>';
                
                response.message.plants.forEach(plant => {
                    const option = document.createElement('option');
                    option.value = plant.plant_name;
                    option.textContent = `${plant.plant_name} (${plant.plant_code})`;
                    plantSelect.appendChild(option);
                });
                
                // Restore saved plant
                if (this.settings.defaultPlant) {
                    plantSelect.value = this.settings.defaultPlant;
                    this.currentPlant = this.settings.defaultPlant;
                    this.updatePlantIndicator();
                }
            }
        } catch (error) {
            console.error('Error loading plants:', error);
        }
    }
    
    async processScan(barcode) {
        if (!barcode.trim()) return;
        
        this.showLoading('Processing scan...');
        
        try {
            // Call scan API
            const response = await frappe.call({
                method: 'amb_w_tds.api.container_api.scan_barcode',
                args: {
                    barcode: barcode,
                    plant: this.currentPlant
                }
            });
            
            if (response.message && response.message.success) {
                this.currentContainer = response.message.container;
                this.displayCurrentContainer();
                this.addToHistory(barcode, 'success', 'Container found');
                this.playSound('success');
            } else {
                this.addToHistory(barcode, 'error', response.message.message);
                this.showAlert('Container not found', 'error');
                this.playSound('error');
            }
        } catch (error) {
            // Add to offline queue
            this.addToOfflineQueue({
                type: 'scan',
                barcode: barcode,
                plant: this.currentPlant,
                timestamp: new Date().toISOString()
            });
            
            this.addToHistory(barcode, 'pending', 'Queued for sync');
            this.showAlert('Saved offline - will sync when online', 'warning');
        }
        
        this.hideLoading();
    }
    
    displayCurrentContainer() {
        if (!this.currentContainer) return;
        
        const container = this.currentContainer;
        const display = document.getElementById('current-container-display');
        
        document.getElementById('container-id').textContent = container.name;
        document.getElementById('container-type').textContent = container.container_type;
        document.getElementById('container-status').textContent = container.lifecycle_status;
        document.getElementById('container-weight').textContent = 
            container.net_weight ? `${container.net_weight} kg` : 'Not set';
        
        // Color-code status
        const statusElement = document.getElementById('container-status');
        statusElement.className = `status-${container.lifecycle_status.toLowerCase()}`;
        
        display.style.display = 'block';
    }
    
    clearCurrentContainer() {
        this.currentContainer = null;
        document.getElementById('current-container-display').style.display = 'none';
    }
    
    async saveCurrentContainer() {
        if (!this.currentContainer) return;
        
        this.showLoading('Saving container...');
        
        try {
            // Save any changes made to current container
            await frappe.call({
                method: 'frappe.client.save',
                args: {
                    doc: this.currentContainer
                }
            });
            
            this.showAlert('Container saved successfully', 'success');
            this.playSound('success');
        } catch (error) {
            this.showAlert('Error saving container', 'error');
            this.playSound('error');
        }
        
        this.hideLoading();
    }
    
    openWeightDialog() {
        if (!this.currentContainer) {
            this.showAlert('Please scan a container first', 'warning');
            return;
        }
        
        const grossWeight = prompt('Enter gross weight (kg):', this.currentContainer.gross_weight || '');
        if (grossWeight && !isNaN(grossWeight)) {
            this.updateContainerWeight(parseFloat(grossWeight));
        }
    }
    
    async updateContainerWeight(grossWeight) {
        this.showLoading('Calculating weights...');
        
        try {
            const response = await frappe.call({
                method: 'amb_w_tds.api.container_api.calculate_weights',
                args: {
                    container_name: this.currentContainer.name,
                    gross_weight: grossWeight
                }
            });
            
            if (response.message && response.message.success) {
                // Update current container with new weights
                this.currentContainer.gross_weight = response.message.gross_weight;
                this.currentContainer.net_weight = response.message.net_weight;
                this.currentContainer.tara_weight = response.message.tara_weight;
                
                this.displayCurrentContainer();
                this.showAlert('Weights calculated successfully', 'success');
            } else {
                this.showAlert('Error calculating weights', 'error');
            }
        } catch (error) {
            // Add to offline queue
            this.addToOfflineQueue({
                type: 'weight_update',
                container: this.currentContainer.name,
                gross_weight: grossWeight,
                timestamp: new Date().toISOString()
            });
            
            this.showAlert('Weight update queued for sync', 'warning');
        }
        
        this.hideLoading();
    }
    
    openStatusDialog() {
        if (!this.currentContainer) {
            this.showAlert('Please scan a container first', 'warning');
            return;
        }
        
        const statuses = ['Available', 'Reserved', 'In_Use', 'Completed', 'Maintenance'];
        const currentStatus = this.currentContainer.lifecycle_status;
        
        let options = statuses.map(status => 
            `<option value="${status}" ${status === currentStatus ? 'selected' : ''}>${status}</option>`
        ).join('');
        
        const html = `
            <div class="modal-dialog">
                <h3>Update Container Status</h3>
                <select id="status-select">${options}</select>
                <textarea id="status-notes" placeholder="Notes (optional)"></textarea>
                <div class="modal-actions">
                    <button onclick="mobileScanner.updateContainerStatus()">Update</button>
                    <button onclick="mobileScanner.closeDialog()">Cancel</button>
                </div>
            </div>
        `;
        
        this.showDialog(html);
    }
    
    async updateContainerStatus() {
        const newStatus = document.getElementById('status-select').value;
        const notes = document.getElementById('status-notes').value;
        
        this.closeDialog();
        this.showLoading('Updating status...');
        
        try {
            const response = await frappe.call({
                method: 'amb_w_tds.api.container_api.update_status',
                args: {
                    container_name: this.currentContainer.name,
                    new_status: newStatus,
                    notes: notes
                }
            });
            
            if (response.message && response.message.success) {
                this.currentContainer.lifecycle_status = newStatus;
                this.displayCurrentContainer();
                this.showAlert('Status updated successfully', 'success');
            } else {
                this.showAlert('Error updating status', 'error');
            }
        } catch (error) {
            this.addToOfflineQueue({
                type: 'status_update',
                container: this.currentContainer.name,
                new_status: newStatus,
                notes: notes,
                timestamp: new Date().toISOString()
            });
            
            this.showAlert('Status update queued for sync', 'warning');
        }
        
        this.hideLoading();
    }
    
    openBatchDialog() {
        if (!this.currentContainer) {
            this.showAlert('Please scan a container first', 'warning');
            return;
        }
        
        const batchName = prompt('Enter Batch AMB name:', this.currentContainer.batch_amb_link || '');
        if (batchName) {
            this.assignToBatch(batchName);
        }
    }
    
    async assignToBatch(batchName) {
        this.showLoading('Assigning to batch...');
        
        try {
            const response = await frappe.call({
                method: 'amb_w_tds.api.container_api.assign_to_batch',
                args: {
                    container_name: this.currentContainer.name,
                    batch_amb_name: batchName
                }
            });
            
            if (response.message && response.message.success) {
                this.currentContainer.batch_amb_link = batchName;
                this.currentContainer.lifecycle_status = 'Reserved';
                this.displayCurrentContainer();
                this.showAlert('Assigned to batch successfully', 'success');
            } else {
                this.showAlert('Error assigning to batch', 'error');
            }
        } catch (error) {
            this.addToOfflineQueue({
                type: 'batch_assign',
                container: this.currentContainer.name,
                batch_name: batchName,
                timestamp: new Date().toISOString()
            });
            
            this.showAlert('Batch assignment queued for sync', 'warning');
        }
        
        this.hideLoading();
    }
    
    addToHistory(barcode, status, message) {
        const historyList = document.getElementById('scan-history-list');
        const timestamp = new Date().toLocaleTimeString();
        
        const historyItem = document.createElement('div');
        historyItem.className = `history-item ${status}`;
        historyItem.innerHTML = `
            <div>
                <strong>${barcode}</strong><br>
                <small>${message} - ${timestamp}</small>
            </div>
            <span class="status-badge">${status}</span>
        `;
        
        historyList.insertBefore(historyItem, historyList.firstChild);
        
        // Keep only last 20 items
        while (historyList.children.length > 20) {
            historyList.removeChild(historyList.lastChild);
        }
    }
    
    addToOfflineQueue(operation) {
        this.scanQueue.push(operation);
        this.saveOfflineQueue();
        this.updateQueueCount();
    }
    
    async syncAllPending() {
        if (!this.isOnline || this.scanQueue.length === 0) return;
        
        this.showLoading('Syncing pending operations...');
        
        const successCount = 0;
        const failedOperations = [];
        
        for (const operation of this.scanQueue) {
            try {
                await this.syncOperation(operation);
                successCount++;
            } catch (error) {
                failedOperations.push(operation);
            }
        }
        
        // Remove successful operations
        this.scanQueue = failedOperations;
        this.saveOfflineQueue();
        this.updateQueueCount();
        
        this.hideLoading();
        this.showAlert(`Synced ${successCount} operations`, 'success');
    }
    
    async syncOperation(operation) {
        switch (operation.type) {
            case 'scan':
                return await frappe.call({
                    method: 'amb_w_tds.api.container_api.scan_barcode',
                    args: { barcode: operation.barcode, plant: operation.plant }
                });
                
            case 'weight_update':
                return await frappe.call({
                    method: 'amb_w_tds.api.container_api.calculate_weights',
                    args: { 
                        container_name: operation.container, 
                        gross_weight: operation.gross_weight 
                    }
                });
                
            case 'status_update':
                return await frappe.call({
                    method: 'amb_w_tds.api.container_api.update_status',
                    args: {
                        container_name: operation.container,
                        new_status: operation.new_status,
                        notes: operation.notes
                    }
                });
                
            case 'batch_assign':
                return await frappe.call({
                    method: 'amb_w_tds.api.container_api.assign_to_batch',
                    args: {
                        container_name: operation.container,
                        batch_amb_name: operation.batch_name
                    }
                });
        }
    }
    
    // Utility methods
    updateOnlineStatus() {
        const indicator = document.getElementById('online-status');
        indicator.textContent = this.isOnline ? '●' : '●';
        indicator.className = `status-indicator ${this.isOnline ? 'online' : 'offline'}`;
    }
    
    updatePlantIndicator() {
        document.getElementById('plant-indicator').textContent = this.currentPlant || 'No Plant';
    }
    
    updateQueueCount() {
        document.getElementById('queue-count').textContent = `Queue: ${this.scanQueue.length}`;
    }
    
    showLoading(message) {
        // Implement loading indicator
        console.log(message);
    }
    
    hideLoading() {
        // Hide loading indicator
    }
    
    showAlert(message, type) {
        // Show mobile-friendly alert
        alert(message);
    }
    
    showDialog(html) {
        // Show modal dialog
        const dialog = document.createElement('div');
        dialog.className = 'mobile-dialog-overlay';
        dialog.innerHTML = html;
        document.body.appendChild(dialog);
    }
    
    closeDialog() {
        const dialog = document.querySelector('.mobile-dialog-overlay');
        if (dialog) {
            dialog.remove();
        }
    }
    
    playSound(type) {
        if (!this.settings.soundEnabled) return;
        
        // Implement sound alerts for different actions
        const audio = new Audio();
        audio.volume = 0.3;
        
        switch (type) {
            case 'success':
                audio.src = 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N+QQAoUXrTp66hVFApGn+DyvmwfCCWN1PfUf0INHmHA7+KYUxwTW7bm7qBOKgIv0LW5tTUuMqc3n4yTdQMfOo2CqCXBZhwTYLbq3KNZGgc+n+DapmAhCC8w0+Phf1ASXL7i46NTFAI1dB4ABAAQrAAAAANYJCgAJLgIwCxjNzQAAAAA';
                break;
            case 'error':
                audio.src = 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N+QQAoUXrTp66hVFApGn+DyvmwfCCWN1PfUf0INHmHA7+KYUxwTW7bm7qBOKgIv0LW5tTUuMqc3n4yTdQMfOo2CqCXBZhwTYLbq3KNZGgc+n+DapmAhCC8w0+Phf1ASXL7i46NTFAI1dB4ABAAQrAAAAANYJCgAJLgIwCxjNzQAAAAA';
                break;
        }
        
        audio.play().catch(e => console.log('Sound play failed:', e));
    }
    
    loadSettings() {
        const saved = localStorage.getItem('mobile-scanner-settings');
        return saved ? JSON.parse(saved) : {
            defaultPlant: null,
            autoSync: true,
            soundEnabled: true,
            syncInterval: 30
        };
    }
    
    saveSettings() {
        this.settings.defaultPlant = this.currentPlant;
        localStorage.setItem('mobile-scanner-settings', JSON.stringify(this.settings));
    }
    
    loadOfflineQueue() {
        const saved = localStorage.getItem('mobile-scanner-queue');
        this.scanQueue = saved ? JSON.parse(saved) : [];
        this.updateQueueCount();
    }
    
    saveOfflineQueue() {
        localStorage.setItem('mobile-scanner-queue', JSON.stringify(this.scanQueue));
    }
}

// Initialize mobile scanner when page loads
if (typeof frappe !== 'undefined') {
    frappe.ready(() => {
        // Only initialize if we're on the mobile scanner page
        if (window.location.hash.includes('mobile-scanner') || 
            document.getElementById('mobile-scanner-container')) {
            window.mobileScanner = new MobileContainerScanner();
        }
    });
} else {
    // Standalone mode
    document.addEventListener('DOMContentLoaded', () => {
        window.mobileScanner = new MobileContainerScanner();
    });
}