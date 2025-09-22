document.addEventListener('DOMContentLoaded', function() {
    // Get the greeting element
    const greetingElement = document.getElementById('greeting');
    
    // Function to update greeting based on time of day
    function updateGreeting() {
        const hour = new Date().getHours();
        let greeting;
        
        if (hour < 12) {
            greeting = 'Good morning, IT Department!';
        } else if (hour < 18) {
            greeting = 'Good afternoon, IT Department!';
        } else {
            greeting = 'Good evening, IT Department!';
        }
        
        // Add animation class
        greetingElement.style.opacity = '0';
        greetingElement.style.transform = 'translateY(10px)';
        
        // Update text after animation
        setTimeout(() => {
            greetingElement.textContent = greeting;
            greetingElement.style.opacity = '1';
            greetingElement.style.transform = 'translateY(0)';
        }, 300);
    }
    
    // Initial update
    updateGreeting();
    
    // Update greeting every hour
    setInterval(updateGreeting, 3600000);
});
