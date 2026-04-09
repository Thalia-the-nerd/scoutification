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
        this.form.innerHTML = ''; // clear

        // 1. Create Tab Buttons
        const tabContainer = document.createElement('div');
        tabContainer.className = 'tab-container';

        // 2. Create Tab Content Areas
        const tabContents = {};

        CONFIG.tabs.forEach((tab, index) => {
            // Tab Button
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `tab-btn ${index === 0 ? 'active' : ''}`;
            btn.textContent = tab.label;
            btn.dataset.target = tab.id;

            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');

                e.target.classList.add('active');
                document.getElementById(tab.id).style.display = 'block';
                this.form.dataset.activeTab = tab.id; // Track which tab is active for submission
            });

            tabContainer.appendChild(btn);

            // Tab Content Div
            const content = document.createElement('div');
            content.id = tab.id;
            content.className = `tab-content`;
            content.style.display = index === 0 ? 'block' : 'none';
            tabContents[tab.id] = content;
        });

        this.form.dataset.activeTab = CONFIG.tabs[0].id;
        this.form.appendChild(tabContainer);

        // Group fields by category
        const categorizedFields = {};
        CONFIG.fields.forEach(field => {
            if (!categorizedFields[field.category]) categorizedFields[field.category] = [];
            categorizedFields[field.category].push(field);
        });

        // Render each category section into the correct tab
        Object.keys(CONFIG.categories).forEach(categoryKey => {
            if (!categorizedFields[categoryKey]) return;

            // Filter out wifi_only fields for the QR code submission side
            const fieldsToRender = categorizedFields[categoryKey].filter(f => !f.wifi_only);
            if (fieldsToRender.length === 0) return;

            const categoryMeta = CONFIG.categories[categoryKey];
            const section = document.createElement('div');
            section.className = 'form-section';

            const heading = document.createElement('h2');
            heading.textContent = categoryMeta.label;
            section.appendChild(heading);

            // Optional warning note (e.g., photo limits)
            if (categoryMeta.note) {
                const note = document.createElement('p');
                note.className = 'category-note';
                note.textContent = categoryMeta.note;
                section.appendChild(note);
            }

            fieldsToRender.forEach(field => {
                const formGroup = this.createFormField(field);
                section.appendChild(formGroup);
            });

            // Append to the specific tab defined in config
            if (tabContents[categoryMeta.tab]) {
                tabContents[categoryMeta.tab].appendChild(section);
            }
        });

        Object.values(tabContents).forEach(content => {
            this.form.appendChild(content);
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
            case 'file':
                input = this.createFileInput(field);
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

    createFileInput(field) {
        const input = document.createElement('input');
        input.type = 'file';
        input.id = field.id;
        input.name = field.id;
        if (field.accept) input.accept = field.accept;

        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) {
                delete this.formData[field.id];
                this.saveToLocalStorage();
                return;
            }

            // Downscale image to save space
            const reader = new FileReader();
            reader.onload = (event) => {
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');

                    const MAX_WIDTH = 600;
                    const MAX_HEIGHT = 600;
                    let width = img.width;
                    let height = img.height;

                    if (width > height) {
                        if (width > MAX_WIDTH) {
                            height *= MAX_WIDTH / width;
                            width = MAX_WIDTH;
                        }
                    } else {
                        if (height > MAX_HEIGHT) {
                            width *= MAX_HEIGHT / height;
                            height = MAX_HEIGHT;
                        }
                    }

                    canvas.width = width;
                    canvas.height = height;
                    ctx.drawImage(img, 0, 0, width, height);

                    // Compress as JPEG
                    this.formData[field.id] = canvas.toDataURL('image/jpeg', 0.6);
                    this.saveToLocalStorage();
                };
                img.src = event.target.result;
            };
            reader.readAsDataURL(file);
        });

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

        const activeTab = this.form.dataset.activeTab;

        CONFIG.fields.forEach(field => {
            // Only collect fields for the active tab
            const categoryMeta = CONFIG.categories[field.category];
            if (!categoryMeta || categoryMeta.tab !== activeTab) return;

            if (field.type === 'counter') {
                data[field.id] = this.counterValues[field.id] || 0;
            } else if (field.type === 'checkbox') {
                const checkbox = document.getElementById(field.id);
                data[field.id] = checkbox ? checkbox.checked : false;
            } else if (field.type === 'file') {
                data[field.id] = this.formData[field.id] || '';
            } else {
                const element = document.getElementById(field.id);
                data[field.id] = element ? element.value : '';
            }
        });

        return data;
    }

    validateFormData(data) {
        const errors = [];
        const activeTab = this.form.dataset.activeTab;

        CONFIG.fields.forEach(field => {
            const categoryMeta = CONFIG.categories[field.category];
            if (!categoryMeta || categoryMeta.tab !== activeTab) return;

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

        // Remove base64 image data before generating QR code due to size limits
        const qrData = { ...data };
        CONFIG.fields.forEach(field => {
            if (field.type === 'file') {
                delete qrData[field.id];
            }
        });

        // Compress data for QR code (remove whitespace)
        const jsonString = JSON.stringify(qrData);

        // Generate QR Code
        this.generateQR(jsonString, qrData);

        // Save to history (save full data including photo)
        this.saveToHistory(data);

        this.showStatus('QR Code generated successfully!', 'success');
    }

    generateQR(jsonString, data) {
        // Clear previous QR code
        const qrcodeContainer = document.getElementById('qrcode');
        qrcodeContainer.innerHTML = '';

        // Generate new QR code — pass the container div directly (qrcodejs API)
        try {
            new QRCode(qrcodeContainer, {
                text: jsonString,
                width: 256,
                height: 256,
                colorDark: '#000000',
                colorLight: '#ffffff',
                correctLevel: QRCode.CorrectLevel.H
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
