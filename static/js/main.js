/* ============================================================
   Smart Gram Panchayat Complaint Portal – Main JavaScript
   Vanilla JS, no jQuery dependency
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

    /* ----- Tooltip Initialization ----- */
    var tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function (el) {
        return new bootstrap.Tooltip(el);
    });

    /* ----- Image Preview on File Input ----- */
    var fileInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    fileInputs.forEach(function (input) {
        input.addEventListener('change', function (e) {
            var file = e.target.files[0];
            if (!file) return;

            // Remove any existing preview
            var existingPreview = input.parentElement.querySelector('.img-preview');
            if (existingPreview) existingPreview.remove();

            var reader = new FileReader();
            reader.onload = function (ev) {
                var img = document.createElement('img');
                img.src = ev.target.result;
                img.alt = 'Image preview';
                img.className = 'img-preview mt-2 rounded';
                img.style.maxWidth = '200px';
                img.style.maxHeight = '200px';
                img.style.objectFit = 'contain';
                input.parentElement.appendChild(img);
            };
            reader.readAsDataURL(file);
        });
    });

    /* ----- Confirm Dialogs for Destructive Actions ----- */
    document.querySelectorAll('[data-confirm]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            var message = el.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Specific named confirms
    document.querySelectorAll('.btn-reopen').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (!confirm('Are you sure you want to reopen this complaint?')) {
                e.preventDefault();
            }
        });
    });

    document.querySelectorAll('.btn-confirm-duplicate').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (!confirm('Confirm this complaint as a duplicate?')) {
                e.preventDefault();
            }
        });
    });

    document.querySelectorAll('.btn-reject-duplicate').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (!confirm('Reject this duplicate relationship?')) {
                e.preventDefault();
            }
        });
    });

    /* ----- Auto-Dismiss Flash Messages after 5 seconds ----- */
    var alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    /* ----- Character Counter for Description Textarea ----- */
    var descTextarea = document.getElementById('description');
    if (descTextarea) {
        var maxLen = parseInt(descTextarea.getAttribute('maxlength')) || 1000;

        // Create counter element if not present
        var counter = descTextarea.parentElement.querySelector('.char-counter');
        if (!counter) {
            counter = document.createElement('small');
            counter.className = 'char-counter text-muted d-block text-end';
            descTextarea.parentElement.appendChild(counter);
        }

        function updateCounter() {
            var remaining = maxLen - descTextarea.value.length;
            counter.textContent = remaining + ' / ' + maxLen + ' characters remaining';
            if (remaining < 50) {
                counter.classList.add('text-danger');
                counter.classList.remove('text-muted');
            } else {
                counter.classList.remove('text-danger');
                counter.classList.add('text-muted');
            }
        }

        descTextarea.addEventListener('input', updateCounter);
        updateCounter(); // initial count
    }

    /* ----- Form Validation Helpers ----- */
    var forms = document.querySelectorAll('form[novalidate], form.needs-validation');
    forms.forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');

            // Highlight invalid fields with Bootstrap's is-invalid class
            form.querySelectorAll(':invalid').forEach(function (field) {
                field.classList.add('is-invalid');
            });
            form.querySelectorAll(':valid').forEach(function (field) {
                field.classList.remove('is-invalid');
            });
        });

        // Clear is-invalid on input
        form.querySelectorAll('.form-control, .form-select').forEach(function (field) {
            field.addEventListener('input', function () {
                if (field.checkValidity()) {
                    field.classList.remove('is-invalid');
                }
            });
        });
    });

    /* ----- Notification Badge Update (Visual) ----- */
    var notifBadge = document.querySelector('.notif-badge');
    if (notifBadge) {
        var count = parseInt(notifBadge.textContent) || 0;
        if (count === 0) {
            notifBadge.style.display = 'none';
        }
    }

});
