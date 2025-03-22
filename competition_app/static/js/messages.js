document.addEventListener('DOMContentLoaded', function() {
    // Function to fade out an element
    function fadeOut(element) {
        let opacity = 1;
        const timer = setInterval(function() {
            if (opacity <= 0.1) {
                clearInterval(timer);
                element.style.display = 'none';
                element.remove();
            }
            element.style.opacity = opacity;
            opacity -= opacity * 0.1;
        }, 50);
    }

    // Get all message elements
    const messages = document.querySelectorAll('.message');
    
    // Fade out each message after 2 seconds
    messages.forEach(function(message) {
        setTimeout(function() {
            fadeOut(message);
        }, 2000);
    });
});
