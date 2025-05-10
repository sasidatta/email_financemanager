// Fetch emails from the server and display status
function fetchEmails() {
    const result = document.getElementById("result");
    if (!result) return;
    result.textContent = 'Fetching emails...';
    fetch('/fetch-emails')
        .then(response => response.json())
        .then(data => {
            result.textContent =
                `Inserted: ${data.inserted} emails\n` +
                `Message: ${data.message}\n` +
                `Start Date: ${data.start_date}\n` +
                `Last Email Timestamp: ${data.last_timestamp}`;
        })
        .catch(() => {
            result.textContent = 'Error fetching emails.';
        });
}

// Clean up emails on the server and display status
function cleanupEmails() {
    const result = document.getElementById("result");
    if (!result) return;
    result.textContent = 'Cleaning up emails...';
    fetch('/cleanup-emails')
        .then(response => response.json())
        .then(data => {
            result.textContent =
                `Deleted: ${data.deleted} emails\n` +
                `Message: ${data.message}`;
        })
        .catch(() => {
            result.textContent = 'Error cleaning up emails.';
        });
}

// Confirm before deleting a transaction
window.confirmDelete = function() {
    return confirm("Are you sure you want to delete this transaction?");
}

// Toggle sorting for table columns (ascending/descending)
let sortAscending = true;
window.toggleSort = function(header) {
    sortAscending = !sortAscending;
    console.log(`Sorting by ${header} in ${sortAscending ? 'ASC' : 'DESC'} order`);
    // Add logic here to sort your table data accordingly
}

// Update pagination UI (disable previous/next buttons as needed)
window.updatePagination = function(page, totalPages) {
    const prevButton = document.getElementById("prev-button");
    const nextButton = document.getElementById("next-button");
    if (!prevButton || !nextButton) return;

    prevButton.disabled = page <= 1;
    nextButton.disabled = page >= totalPages;

    const pageIndicator = document.getElementById("page-number");
    if (pageIndicator) {
        pageIndicator.textContent = `Page ${page} of ${totalPages}`;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    // Functions already assigned to window scope
});