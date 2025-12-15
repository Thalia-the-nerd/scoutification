// FRC Scouting System - Main Application Logic

class ScoutingApp {
    constructor() {
        this.form = document.getElementById('scouting-form');
        this.submitBtn = document.getElementById('submit-btn');
        this.resetBtn = document.getElementById('reset-btn');
        this.newEntryBtn = document.getElementById('new-entry-btn');
        this.qrDisplay = document.getElementById('qr-display');
        this.statusContainer = document.getElementById('status-container');
        this.historyContainer = document.getElementById('history-container');
        
        this.formData = {};
        this.counterValues = {};
        
        this.init();
    }
    
    init() {
        this.renderForm();
        this.attachEventListeners();
        this.loadHistory();
        this.loadFromLocalStorage();
    }
    
    renderForm() {
        // Group fields by category
        const categorizedFields = {};
        
        CONFIG.fields.forEach(field => {
            if (!categorizedFields[field.category]) {
                categorizedFields[field.category] = [];
            }
            categorizedFields[field.category].push(field);
        });
        
        // Render each category section
        Object.keys(CONFIG.categories).forEach(categoryKey => {
            if (!categorizedFields[categoryKey]) return;
            
            const section = document.createElement('div');
            section.className = 'form-section';
            
            const heading = document.createElement('h2');
            heading.textContent = CONFIG.categories[categoryKey];
            section.appendChild(heading);
            
            categorizedFields[categoryKey].forEach(field => {
                const formGroup = this.createFormField(field);
                section.appendChild(formGroup);
            });
            
            this.form.appendChild(section);
        });
    }
    
    createFormField(field) {
        const formGroup = document.createElement('div');
        formGroup.className = 'form-group';
        
        const label = document.createElement('label');
        label.textContent = field.label + (field.required ? ' *' : '');
        label.setAttribute('for', field.id);
        formGroup.appendChild(label);
        
        let input;
        
        switch (field.type) {
            case 'counter':
                input = this.createCounterControl(field);
                break;
            case 'checkbox':
                input = this.createCheckbox(field);
                break;
            case 'dropdown':
                input = this.createDropdown(field);
                break;
            case 'textarea':
                input = this.createTextarea(field);
                break;
            case 'number':
                input = this.createNumberInput(field);
                break;
            case 'text':
            default:
                input = this.createTextInput(field);
                break;
        }
        
        formGroup.appendChild(input);
        return formGroup;
    }
    
    createCounterControl(field) {
        const wrapper = document.createElement('div');
        wrapper.className = 'counter-control';
        
        const minusBtn = document.createElement('button');
        minusBtn.type = 'button';
        minusBtn.className = 'counter-btn minus';
        minusBtn.textContent = '−';
        
        const valueDisplay = document.createElement('div');
        valueDisplay.className = 'counter-value';
        valueDisplay.textContent = '0';
        valueDisplay.id = field.id + '-value';
        
        const plusBtn = document.createElement('button');
        plusBtn.type = 'button';
        plusBtn.className = 'counter-btn plus';
        plusBtn.textContent = '+';
        
        // Initialize counter value
        this.counterValues[field.id] = 0;
        
        // Event listeners
        minusBtn.addEventListener('click', () => {
            const currentValue = this.counterValues[field.id];
            const minValue = field.min !== undefined ? field.min : 0;
            if (currentValue > minValue) {
                this.counterValues[field.id]--;
                valueDisplay.textContent = this.counterValues[field.id];
                this.saveToLocalStorage();
            }
        });
        
        plusBtn.addEventListener('click', () => {
            const currentValue = this.counterValues[field.id];
            const maxValue = field.max !== undefined ? field.max : 999;
            if (currentValue < maxValue) {
                this.counterValues[field.id]++;
                valueDisplay.textContent = this.counterValues[field.id];
                this.saveToLocalStorage();
            }
        });
        
        wrapper.appendChild(minusBtn);
        wrapper.appendChild(valueDisplay);
        wrapper.appendChild(plusBtn);
        
        return wrapper;
    }
    
    createCheckbox(field) {
        const wrapper = document.createElement('div');
        wrapper.className = 'checkbox-wrapper';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = field.id;
        checkbox.name = field.id;
        
        const label = document.createElement('label');
        label.textContent = 'Yes';
        label.setAttribute('for', field.id);
        label.style.marginBottom = '0';
        
        wrapper.appendChild(checkbox);
        wrapper.appendChild(label);
        
        checkbox.addEventListener('change', () => this.saveToLocalStorage());
        
        return wrapper;
    }
    
    createDropdown(field) {
        const select = document.createElement('select');
        select.id = field.id;
        select.name = field.id;
        select.required = field.required || false;
        
        // Add default empty option if not required
        if (!field.required) {
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = '-- Select --';
            select.appendChild(defaultOption);
        }
        
        // Add options
        field.options.forEach(optionText => {
            const option = document.createElement('option');
            option.value = optionText;
            option.textContent = optionText;
            select.appendChild(option);
        });
        
        select.addEventListener('change', () => this.saveToLocalStorage());
        
        return select;
    }
    
    createTextarea(field) {
        const textarea = document.createElement('textarea');
        textarea.id = field.id;
        textarea.name = field.id;
        textarea.placeholder = field.label;
        
        textarea.addEventListener('input', () => this.saveToLocalStorage());
        
        return textarea;
    }
    
    createNumberInput(field) {
        const input = document.createElement('input');
        input.type = 'number';
        input.id = field.id;
        input.name = field.id;
        input.required = field.required || false;
        input.placeholder = field.label;
        
        if (field.min !== undefined) input.min = field.min;
        if (field.max !== undefined) input.max = field.max;
        
        input.addEventListener('input', () => this.saveToLocalStorage());
        
        return input;
    }
    
    createTextInput(field) {
        const input = document.createElement('input');
        input.type = 'text';
        input.id = field.id;
        input.name = field.id;
        input.required = field.required || false;
        input.placeholder = field.label;
        
        input.addEventListener('input', () => this.saveToLocalStorage());
        
        return input;
    }
    
    attachEventListeners() {
        this.submitBtn.addEventListener('click', () => this.handleSubmit());
        this.resetBtn.addEventListener('click', () => this.handleReset());
        this.newEntryBtn.addEventListener('click', () => this.handleNewEntry());
    }
    
    collectFormData() {
        const data = {
            timestamp: new Date().toISOString()
        };
        
        CONFIG.fields.forEach(field => {
            if (field.type === 'counter') {
                data[field.id] = this.counterValues[field.id] || 0;
            } else if (field.type === 'checkbox') {
                const checkbox = document.getElementById(field.id);
                data[field.id] = checkbox ? checkbox.checked : false;
            } else {
                const element = document.getElementById(field.id);
                data[field.id] = element ? element.value : '';
            }
        });
        
        return data;
    }
    
    validateFormData(data) {
        const errors = [];
        
        CONFIG.fields.forEach(field => {
            if (field.required) {
                const value = data[field.id];
                if (value === '' || value === null || value === undefined) {
                    errors.push(`${field.label} is required`);
                }
            }
        });
        
        return errors;
    }
    
    handleSubmit() {
        const data = this.collectFormData();
        const errors = this.validateFormData(data);
        
        if (errors.length > 0) {
            this.showStatus(errors.join('<br>'), 'error');
            return;
        }
        
        // Compress data for QR code (remove whitespace)
        const jsonString = JSON.stringify(data);
        
        // Generate QR Code
        this.generateQR(jsonString, data);
        
        // Save to history
        this.saveToHistory(data);
        
        this.showStatus('QR Code generated successfully!', 'success');
    }
    
    generateQR(jsonString, data) {
        // Clear previous QR code
        const qrcodeContainer = document.getElementById('qrcode');
        qrcodeContainer.innerHTML = '';
        
        // Create SVG element for QR code
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '256');
        svg.setAttribute('height', '256');
        qrcodeContainer.appendChild(svg);
        
        // Generate new QR code
        try {
            new QRCode(svg, {
                text: jsonString,
                width: 256,
                height: 256,
                colorDark: '#000000',
                colorLight: '#ffffff',
                correctLevel: QRCode.CorrectLevel.M,
                useSVG: true
            });
        } catch (e) {
            console.error('QR Code generation error:', e);
            this.showStatus('Error generating QR code: ' + e.message, 'error');
            return;
        }
        
        // Update display info
        document.getElementById('qr-match-num').textContent = data.match_number || 'N/A';
        document.getElementById('qr-team-num').textContent = data.team_number || 'N/A';
        
        // Show QR display
        this.qrDisplay.classList.add('active');
        
        // Scroll to QR code
        this.qrDisplay.scrollIntoView({ behavior: 'smooth' });
    }
    
    handleReset() {
        if (confirm('Are you sure you want to reset the form?')) {
            // Reset all counter values
            Object.keys(this.counterValues).forEach(key => {
                this.counterValues[key] = 0;
                const valueDisplay = document.getElementById(key + '-value');
                if (valueDisplay) {
                    valueDisplay.textContent = '0';
                }
            });
            
            // Reset form inputs
            this.form.reset();
            
            // Clear localStorage
            localStorage.removeItem('scoutingFormDraft');
            
            this.showStatus('Form reset successfully', 'success');
        }
    }
    
    handleNewEntry() {
        this.handleReset();
        this.qrDisplay.classList.remove('active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    saveToLocalStorage() {
        const data = this.collectFormData();
        localStorage.setItem('scoutingFormDraft', JSON.stringify(data));
    }
    
    loadFromLocalStorage() {
        const savedData = localStorage.getItem('scoutingFormDraft');
        if (savedData) {
            try {
                const data = JSON.parse(savedData);
                this.restoreFormData(data);
            } catch (e) {
                console.error('Error loading saved data:', e);
            }
        }
    }
    
    restoreFormData(data) {
        CONFIG.fields.forEach(field => {
            const value = data[field.id];
            if (value === undefined || value === null) return;
            
            if (field.type === 'counter') {
                this.counterValues[field.id] = value;
                const valueDisplay = document.getElementById(field.id + '-value');
                if (valueDisplay) {
                    valueDisplay.textContent = value;
                }
            } else if (field.type === 'checkbox') {
                const checkbox = document.getElementById(field.id);
                if (checkbox) {
                    checkbox.checked = value;
                }
            } else {
                const element = document.getElementById(field.id);
                if (element) {
                    element.value = value;
                }
            }
        });
    }
    
    saveToHistory(data) {
        let history = JSON.parse(localStorage.getItem('scoutingHistory') || '[]');
        history.unshift(data);
        
        // Keep only last 20 entries
        if (history.length > 20) {
            history = history.slice(0, 20);
        }
        
        localStorage.setItem('scoutingHistory', JSON.stringify(history));
        this.loadHistory();
    }
    
    loadHistory() {
        const history = JSON.parse(localStorage.getItem('scoutingHistory') || '[]');
        
        if (history.length === 0) {
            this.historyContainer.innerHTML = '<p class="subtitle">No entries yet.</p>';
            return;
        }
        
        this.historyContainer.innerHTML = '';
        
        history.slice(0, 10).forEach((entry, index) => {
            const item = document.createElement('div');
            item.className = 'history-item';
            
            const timestamp = new Date(entry.timestamp).toLocaleString();
            item.innerHTML = `
                <strong>#${index + 1}</strong> - 
                Match <span>${entry.match_number || 'N/A'}</span> | 
                Team <span>${entry.team_number || 'N/A'}</span> | 
                Alliance <span>${entry.alliance || 'N/A'}</span> | 
                <small>${timestamp}</small>
            `;
            
            this.historyContainer.appendChild(item);
        });
    }
    
    showStatus(message, type) {
        this.statusContainer.innerHTML = `
            <div class="status-message status-${type}">
                ${message}
            </div>
        `;
        
        setTimeout(() => {
            this.statusContainer.innerHTML = '';
        }, 5000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ScoutingApp();
});
