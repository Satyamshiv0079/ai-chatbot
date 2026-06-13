import '@testing-library/jest-dom'

// Mock scrollIntoView since jsdom does not support it
window.HTMLElement.prototype.scrollIntoView = function() {};
