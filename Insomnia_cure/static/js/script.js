// Additional JavaScript functionality can be added here
// Most of the JavaScript is already included in the templates

// Utility function for formatting dates
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

// Utility function for calculating sleep efficiency
function calculateSleepEfficiency(timeInBed, timeAsleep) {
    return Math.round((timeAsleep / timeInBed) * 100);
}

// Export functions for use in other scripts
window.InsomniaCureUtils = {
    formatDate,
    calculateSleepEfficiency
};