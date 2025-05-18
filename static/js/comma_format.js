document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input.comma-separated');
    
    inputs.forEach(input => {
        // Format on input
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^0-9.]/g, ''); // Allow numbers and decimal
            if (value === '') return;
            
            // Split integer and decimal parts
            const parts = value.split('.');
            let integerPart = parts[0];
            const decimalPart = parts.length > 1 ? '.' + parts[1].slice(0, 2) : '';
            
            // Add commas to integer part
            integerPart = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
            
            e.target.value = integerPart + decimalPart;
        });
        
        // Remove commas before form submission
        input.form.addEventListener('submit', function() {
            input.value = input.value.replace(/,/g, '');
        });
    });
});