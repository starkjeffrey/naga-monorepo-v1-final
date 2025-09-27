# Level Testing Implementation Guide

## Quick Start for Developers

This guide provides step-by-step implementation instructions for the redesigned level testing system.

## Step 1: Database Migration

### 1.1 Create New Models

```python
# apps/level_testing/models.py

class TestAccessToken(AuditModel):
    """Pre-application payment token enabling access to application form."""
    
    # Unique identifier
    access_code = models.CharField(
        _("Access Code"),
        max_length=7,
        unique=True,
        db_index=True,
        help_text=_("7-digit code with Luhn check digit")
    )
    
    # Student Information (collected at payment)
    student_name = models.CharField(
        _("Student Name"),
        max_length=100,
        help_text=_("Full name as provided at payment")
    )
    student_phone = models.CharField(
        _("Phone Number"),
        max_length=20,
        db_index=True,
        help_text=_("Primary contact number")
    )
    
    # Payment Details
    payment_amount = models.DecimalField(
        _("Payment Amount"),
        max_digits=8,
        decimal_places=2,
        default=Decimal("5.00")
    )
    payment_method = models.CharField(
        _("Payment Method"),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH
    )
    payment_received_at = models.DateTimeField(
        _("Payment Received At"),
        default=timezone.now
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issued_access_tokens",
        verbose_name=_("Cashier")
    )
    receipt_number = models.CharField(
        _("Receipt Number"),
        max_length=20,
        blank=True,
        help_text=_("Physical receipt number if printed")
    )
    
    # QR Code Information
    qr_code_url = models.URLField(
        _("QR Code URL"),
        max_length=500,
        help_text=_("Full URL encoded in QR code")
    )
    qr_code_data = models.JSONField(
        _("QR Code Data"),
        default=dict,
        help_text=_("Additional QR code metadata")
    )
    
    # Usage Tracking
    is_used = models.BooleanField(
        _("Is Used"),
        default=False,
        help_text=_("Whether this token has been used to start an application")
    )
    used_at = models.DateTimeField(
        _("Used At"),
        null=True,
        blank=True,
        help_text=_("When the token was first used")
    )
    application = models.OneToOneField(
        'PotentialStudent',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="access_token",
        verbose_name=_("Application"),
        help_text=_("The application created with this token")
    )
    
    # Telegram Integration
    telegram_id = models.CharField(
        _("Telegram ID"),
        max_length=50,
        blank=True,
        db_index=True,
        help_text=_("Telegram user ID if verified")
    )
    telegram_username = models.CharField(
        _("Telegram Username"),
        max_length=50,
        blank=True,
        help_text=_("Telegram @username")
    )
    telegram_verified = models.BooleanField(
        _("Telegram Verified"),
        default=False,
        help_text=_("Whether Telegram has been verified")
    )
    telegram_verification_code = models.CharField(
        _("Verification Code"),
        max_length=6,
        blank=True,
        help_text=_("6-digit verification code for Telegram")
    )
    telegram_verified_at = models.DateTimeField(
        _("Telegram Verified At"),
        null=True,
        blank=True
    )
    
    # Expiration
    expires_at = models.DateTimeField(
        _("Expires At"),
        help_text=_("Token expiration time")
    )
    
    class Meta:
        verbose_name = _("Test Access Token")
        verbose_name_plural = _("Test Access Tokens")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["access_code"]),
            models.Index(fields=["student_phone"]),
            models.Index(fields=["is_used"]),
            models.Index(fields=["telegram_id"]),
            models.Index(fields=["expires_at"]),
        ]
    
    def __str__(self):
        return f"{self.access_code} - {self.student_name}"
    
    def save(self, *args, **kwargs):
        if not self.access_code:
            self.access_code = self.generate_access_code()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        if not self.qr_code_url:
            self.qr_code_url = self.generate_qr_url()
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_access_code(cls):
        """Generate unique 7-digit access code with Luhn check."""
        while True:
            # Generate 6 random digits
            base_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            # Calculate Luhn check digit
            check_digit = calculate_luhn_check_digit(base_code)
            access_code = base_code + check_digit
            
            # Ensure uniqueness
            if not cls.objects.filter(access_code=access_code).exists():
                return access_code
    
    def generate_qr_url(self):
        """Generate the URL to encode in QR code."""
        base_url = settings.LEVEL_TESTING_BASE_URL
        return f"{base_url}/apply/{self.access_code}/"
    
    @property
    def is_expired(self):
        """Check if token has expired."""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if token is valid for use."""
        return not self.is_used and not self.is_expired
    
    def mark_used(self, application):
        """Mark token as used and link to application."""
        self.is_used = True
        self.used_at = timezone.now()
        self.application = application
        self.save(update_fields=["is_used", "used_at", "application"])
```

### 1.2 Migration File

```python
# apps/level_testing/migrations/0002_add_access_token_system.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('level_testing', '0001_initial'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='TestAccessToken',
            fields=[
                # ... field definitions from model ...
            ],
        ),
        
        migrations.AddField(
            model_name='potentialstudent',
            name='access_token',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='application',
                to='level_testing.testaccesstoken',
            ),
        ),
        
        migrations.AddField(
            model_name='potentialstudent',
            name='telegram_id',
            field=models.CharField(blank=True, max_length=50),
        ),
        
        migrations.AddField(
            model_name='potentialstudent',
            name='telegram_notifications_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
```

## Step 2: Views Implementation

### 2.1 Cashier Payment Collection View

```python
# apps/level_testing/views.py

class CashierPaymentCollectionView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Quick payment collection interface for cashiers."""
    
    template_name = 'level_testing/cashier/collect_payment.html'
    form_class = CashierPaymentForm
    permission_required = 'level_testing.add_testaccesstoken'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today_tokens'] = TestAccessToken.objects.filter(
            created_at__date=timezone.now().date(),
            cashier=self.request.user
        ).count()
        return context
    
    def form_valid(self, form):
        with transaction.atomic():
            # Create access token
            token = TestAccessToken.objects.create(
                student_name=form.cleaned_data['student_name'],
                student_phone=form.cleaned_data['student_phone'],
                payment_amount=form.cleaned_data['amount'],
                payment_method=form.cleaned_data['payment_method'],
                cashier=self.request.user,
                receipt_number=form.cleaned_data.get('receipt_number', '')
            )
            
            # Generate QR code
            qr_service = QRCodeService()
            qr_image_data = qr_service.generate_qr_code(token)
            
            # Store QR data
            token.qr_code_data = {
                'generated_at': timezone.now().isoformat(),
                'terminal': self.request.META.get('REMOTE_ADDR'),
                'user_agent': self.request.META.get('HTTP_USER_AGENT')
            }
            token.save()
            
            # Print receipt if requested
            if form.cleaned_data.get('print_receipt'):
                try:
                    printer = ThermalPrinterService()
                    printer.print_access_receipt(token, qr_image_data)
                    messages.success(self.request, "Receipt printed successfully")
                except Exception as e:
                    logger.error(f"Failed to print receipt: {e}")
                    messages.warning(self.request, "Receipt could not be printed")
            
            # Log transaction
            logger.info(f"Access token {token.access_code} created by {self.request.user}")
            
            # Show success page with QR code
            return render(self.request, 'level_testing/cashier/payment_success.html', {
                'token': token,
                'qr_code_base64': base64.b64encode(qr_image_data).decode(),
                'print_attempted': form.cleaned_data.get('print_receipt')
            })


class TokenVerificationView(View):
    """Public view to verify access token and start application."""
    
    def get(self, request, access_code):
        """Landing page when scanning QR code."""
        try:
            token = TestAccessToken.objects.get(access_code=access_code)
            
            # Check token validity
            if token.is_expired:
                return render(request, 'level_testing/token_expired.html', {
                    'token': token
                })
            
            if token.is_used:
                # Redirect to existing application
                if token.application:
                    return redirect('level_testing:application_continue', 
                                  application_id=token.application.application_id)
                else:
                    return render(request, 'level_testing/token_used.html', {
                        'token': token
                    })
            
            # Valid token - show welcome page
            return render(request, 'level_testing/token_welcome.html', {
                'token': token,
                'telegram_enabled': settings.TELEGRAM_BOT_ENABLED
            })
            
        except TestAccessToken.DoesNotExist:
            return render(request, 'level_testing/token_invalid.html')
    
    def post(self, request, access_code):
        """Start application with valid token."""
        try:
            token = TestAccessToken.objects.get(access_code=access_code)
            
            if not token.is_valid:
                return JsonResponse({'error': 'Invalid token'}, status=400)
            
            # Create new application
            with transaction.atomic():
                application = PotentialStudent.objects.create(
                    family_name_eng=token.student_name.split()[-1],
                    personal_name_eng=' '.join(token.student_name.split()[:-1]),
                    phone_number=token.student_phone,
                    telegram_id=token.telegram_id if token.telegram_verified else '',
                    telegram_notifications_enabled=token.telegram_verified,
                    status=ApplicationStatus.INITIATED
                )
                
                # Mark token as used
                token.mark_used(application)
                
                # Store in session
                request.session['application_id'] = str(application.application_id)
                request.session['access_code'] = access_code
                
                # Redirect to wizard
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('level_testing:wizard_start')
                })
                
        except TestAccessToken.DoesNotExist:
            return JsonResponse({'error': 'Invalid token'}, status=404)
```

### 2.2 Telegram Integration Views

```python
# apps/level_testing/views.py

class TelegramVerificationView(View):
    """Handle Telegram verification process."""
    
    def post(self, request):
        """Send verification code to Telegram."""
        access_code = request.POST.get('access_code')
        
        try:
            token = TestAccessToken.objects.get(access_code=access_code)
            
            if token.telegram_verified:
                return JsonResponse({
                    'status': 'already_verified',
                    'telegram_username': token.telegram_username
                })
            
            # Generate verification code
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            token.telegram_verification_code = code
            token.save()
            
            # Send via Telegram bot
            telegram_service = TelegramBotService()
            success = telegram_service.send_verification_code(
                phone=token.student_phone,
                code=code,
                student_name=token.student_name
            )
            
            if success:
                return JsonResponse({
                    'status': 'code_sent',
                    'message': 'Verification code sent to your Telegram'
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Could not send code. Please check your Telegram.'
                }, status=400)
                
        except TestAccessToken.DoesNotExist:
            return JsonResponse({'error': 'Invalid token'}, status=404)
    
    def put(self, request):
        """Verify the code entered by user."""
        data = json.loads(request.body)
        access_code = data.get('access_code')
        verification_code = data.get('verification_code')
        
        try:
            token = TestAccessToken.objects.get(access_code=access_code)
            
            # Check code
            if token.telegram_verification_code != verification_code:
                return JsonResponse({
                    'status': 'invalid_code',
                    'message': 'Invalid verification code'
                }, status=400)
            
            # Get Telegram user info
            telegram_service = TelegramBotService()
            user_info = telegram_service.get_user_by_phone(token.student_phone)
            
            if user_info:
                # Update token
                token.telegram_id = user_info['id']
                token.telegram_username = user_info.get('username', '')
                token.telegram_verified = True
                token.telegram_verified_at = timezone.now()
                token.save()
                
                # Send welcome message
                telegram_service.send_welcome_message(
                    telegram_id=user_info['id'],
                    student_name=token.student_name
                )
                
                return JsonResponse({
                    'status': 'verified',
                    'telegram_username': token.telegram_username,
                    'message': 'Telegram verified successfully!'
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Could not verify Telegram account'
                }, status=400)
                
        except TestAccessToken.DoesNotExist:
            return JsonResponse({'error': 'Invalid token'}, status=404)
```

## Step 3: Mobile-First Templates

### 3.1 Token Welcome Page

```html
<!-- templates/level_testing/token_welcome.html -->
{% extends "level_testing/mobile_base.html" %}
{% load i18n static %}

{% block title %}Welcome - Level Testing{% endblock %}

{% block content %}
<div class="mobile-container">
    <!-- Language Toggle -->
    <div class="language-bar">
        <button class="lang-btn active" data-lang="en">English</button>
        <button class="lang-btn" data-lang="km">ខ្មែរ</button>
    </div>
    
    <!-- Welcome Card -->
    <div class="welcome-card">
        <div class="welcome-card__header">
            <img src="{% static 'images/puc-logo.png' %}" alt="PUC" class="logo">
            <h1>{% trans "Welcome to PUC Level Testing" %}</h1>
        </div>
        
        <div class="welcome-card__body">
            <!-- Student Info -->
            <div class="info-section">
                <div class="info-item">
                    <span class="info-label">{% trans "Name" %}:</span>
                    <span class="info-value">{{ token.student_name }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">{% trans "Phone" %}:</span>
                    <span class="info-value">{{ token.student_phone }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">{% trans "Payment" %}:</span>
                    <span class="info-value success">✓ {% trans "Verified" %}</span>
                </div>
            </div>
            
            {% if telegram_enabled and not token.telegram_verified %}
            <!-- Telegram Integration -->
            <div class="telegram-card">
                <div class="telegram-card__icon">
                    <i class="fab fa-telegram"></i>
                </div>
                <div class="telegram-card__content">
                    <h3>{% trans "Connect Telegram" %}</h3>
                    <p>{% trans "Get instant updates about your test" %}</p>
                    <button class="btn btn--telegram" id="connectTelegram">
                        {% trans "Connect Now" %}
                    </button>
                </div>
            </div>
            {% endif %}
            
            {% if token.telegram_verified %}
            <div class="success-message">
                <i class="fas fa-check-circle"></i>
                {% trans "Telegram connected" %}: @{{ token.telegram_username }}
            </div>
            {% endif %}
            
            <!-- Start Application Button -->
            <button class="btn btn--primary btn--large" id="startApplication">
                {% trans "Start Application Form" %}
                <i class="fas fa-arrow-right"></i>
            </button>
            
            <!-- Info Text -->
            <p class="info-text">
                {% trans "The application will take approximately 10-15 minutes to complete." %}
            </p>
        </div>
    </div>
</div>

<!-- Telegram Verification Modal -->
<div class="modal" id="telegramModal" style="display: none;">
    <div class="modal-content">
        <div class="modal-header">
            <h2>{% trans "Verify Telegram" %}</h2>
            <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
            <p>{% trans "We've sent a verification code to your Telegram." %}</p>
            <p>{% trans "Please enter the 6-digit code:" %}</p>
            
            <div class="code-input-group">
                <input type="text" maxlength="1" class="code-input" data-index="0">
                <input type="text" maxlength="1" class="code-input" data-index="1">
                <input type="text" maxlength="1" class="code-input" data-index="2">
                <input type="text" maxlength="1" class="code-input" data-index="3">
                <input type="text" maxlength="1" class="code-input" data-index="4">
                <input type="text" maxlength="1" class="code-input" data-index="5">
            </div>
            
            <button class="btn btn--primary" id="verifyCode">
                {% trans "Verify" %}
            </button>
            
            <p class="resend-text">
                {% trans "Didn't receive code?" %}
                <a href="#" id="resendCode">{% trans "Resend" %}</a>
            </p>
        </div>
    </div>
</div>

<script>
// Initialize welcome page
document.addEventListener('DOMContentLoaded', function() {
    const accessCode = '{{ token.access_code }}';
    
    // Start application
    document.getElementById('startApplication').addEventListener('click', function() {
        fetch(`/level-testing/token/${accessCode}/start/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = data.redirect_url;
            }
        });
    });
    
    // Telegram connection
    const connectBtn = document.getElementById('connectTelegram');
    if (connectBtn) {
        connectBtn.addEventListener('click', function() {
            document.getElementById('telegramModal').style.display = 'block';
            sendVerificationCode();
        });
    }
    
    // Code input auto-advance
    document.querySelectorAll('.code-input').forEach(input => {
        input.addEventListener('input', function(e) {
            if (this.value.length === 1) {
                const nextIndex = parseInt(this.dataset.index) + 1;
                const nextInput = document.querySelector(`.code-input[data-index="${nextIndex}"]`);
                if (nextInput) nextInput.focus();
            }
        });
    });
    
    // Verify code
    document.getElementById('verifyCode').addEventListener('click', function() {
        const code = Array.from(document.querySelectorAll('.code-input'))
            .map(input => input.value)
            .join('');
        
        if (code.length === 6) {
            verifyTelegramCode(code);
        }
    });
    
    function sendVerificationCode() {
        fetch('/level-testing/telegram/send-code/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                access_code: accessCode
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'code_sent') {
                showNotification('Code sent to your Telegram!', 'success');
            }
        });
    }
    
    function verifyTelegramCode(code) {
        fetch('/level-testing/telegram/verify/', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                access_code: accessCode,
                verification_code: code
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'verified') {
                showNotification('Telegram verified successfully!', 'success');
                document.getElementById('telegramModal').style.display = 'none';
                location.reload();
            } else {
                showNotification('Invalid code. Please try again.', 'error');
            }
        });
    }
});
</script>
{% endblock %}
```

### 3.2 Mobile-Optimized Wizard Step

```html
<!-- templates/level_testing/wizard_step_mobile.html -->
{% extends "level_testing/mobile_base.html" %}
{% load i18n widget_tweaks %}

{% block content %}
<div class="wizard-container">
    <!-- Progress Bar -->
    <div class="progress-bar">
        <div class="progress-bar__fill" style="width: {{ progress_percent }}%"></div>
    </div>
    
    <!-- Step Header -->
    <div class="step-header">
        <h2>{{ step_title }}</h2>
        <p class="step-indicator">
            Step <span class="current">{{ step_number }}</span> of {{ total_steps }}
        </p>
    </div>
    
    <!-- Form -->
    <form method="post" class="wizard-form" id="wizardForm">
        {% csrf_token %}
        
        <div class="form-content">
            {% for field in form %}
            <div class="form-group {% if field.errors %}has-error{% endif %}">
                <label for="{{ field.id_for_label }}" 
                       class="{% if field.field.required %}required{% endif %}">
                    {{ field.label }}
                </label>
                
                {% if field.help_text %}
                <p class="help-text">{{ field.help_text }}</p>
                {% endif %}
                
                {{ field|add_class:"form-control" }}
                
                {% if field.errors %}
                <div class="error-message">
                    {{ field.errors.0 }}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        
        <!-- Navigation -->
        <div class="wizard-nav">
            {% if prev_step_url %}
            <a href="{{ prev_step_url }}" class="btn btn--secondary">
                <i class="fas fa-arrow-left"></i>
                {% trans "Previous" %}
            </a>
            {% endif %}
            
            <button type="submit" class="btn btn--primary">
                {% trans "Next" %}
                <i class="fas fa-arrow-right"></i>
            </button>
        </div>
    </form>
    
    <!-- Auto-save indicator -->
    <div class="auto-save-indicator" id="autoSaveIndicator">
        <i class="fas fa-cloud"></i>
        <span>{% trans "Saving..." %}</span>
    </div>
</div>

<script>
// Auto-save functionality
class WizardAutoSave {
    constructor() {
        this.form = document.getElementById('wizardForm');
        this.indicator = document.getElementById('autoSaveIndicator');
        this.saveTimer = null;
        this.init();
    }
    
    init() {
        // Save on input change with debounce
        this.form.addEventListener('input', () => {
            clearTimeout(this.saveTimer);
            this.saveTimer = setTimeout(() => this.save(), 2000);
        });
        
        // Save before page unload
        window.addEventListener('beforeunload', () => this.save());
        
        // Restore from local storage if available
        this.restore();
    }
    
    save() {
        const formData = new FormData(this.form);
        const data = Object.fromEntries(formData);
        
        // Save to localStorage
        localStorage.setItem('wizard_step_{{ step_number }}', JSON.stringify(data));
        
        // Show indicator
        this.indicator.classList.add('active');
        
        // Save to server if online
        if (navigator.onLine) {
            fetch('/level-testing/api/save-progress/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    step: {{ step_number }},
                    data: data
                })
            }).then(() => {
                setTimeout(() => {
                    this.indicator.classList.remove('active');
                }, 1000);
            });
        }
    }
    
    restore() {
        const saved = localStorage.getItem('wizard_step_{{ step_number }}');
        if (saved) {
            const data = JSON.parse(saved);
            Object.keys(data).forEach(key => {
                const field = this.form.elements[key];
                if (field) field.value = data[key];
            });
        }
    }
}

new WizardAutoSave();
</script>
{% endblock %}
```

## Step 4: Services Implementation

### 4.1 QR Code Service

```python
# apps/level_testing/services/qr_service.py

import qrcode
from PIL import Image
from io import BytesIO
import base64

class QRCodeService:
    """Service for generating QR codes for test access tokens."""
    
    def generate_qr_code(self, token: TestAccessToken) -> bytes:
        """Generate QR code image for access token.
        
        Returns:
            Bytes of PNG image
        """
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        # Add data
        qr.add_data(token.qr_code_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Add logo if available
        try:
            logo_path = 'static/images/puc-logo-small.png'
            logo = Image.open(logo_path)
            
            # Calculate logo size (10% of QR code)
            qr_width, qr_height = img.size
            logo_size = min(qr_width, qr_height) // 10
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            
            # Paste logo in center
            logo_pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
            img.paste(logo, logo_pos)
        except Exception:
            # Continue without logo if error
            pass
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def generate_receipt_html(self, token: TestAccessToken, qr_image_bytes: bytes) -> str:
        """Generate HTML receipt for printing.
        
        Returns:
            HTML string for receipt
        """
        qr_base64 = base64.b64encode(qr_image_bytes).decode()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 300px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #000;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }}
                .logo {{
                    width: 80px;
                    height: auto;
                }}
                h1 {{
                    font-size: 18px;
                    margin: 10px 0;
                }}
                .info {{
                    margin: 15px 0;
                }}
                .info-row {{
                    display: flex;
                    justify-content: space-between;
                    margin: 5px 0;
                }}
                .qr-code {{
                    text-align: center;
                    margin: 20px 0;
                }}
                .qr-code img {{
                    width: 200px;
                    height: 200px;
                }}
                .access-code {{
                    font-size: 24px;
                    font-weight: bold;
                    text-align: center;
                    letter-spacing: 2px;
                    margin: 20px 0;
                    padding: 10px;
                    border: 2px solid #000;
                }}
                .footer {{
                    text-align: center;
                    font-size: 12px;
                    margin-top: 20px;
                    padding-top: 10px;
                    border-top: 1px solid #000;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <img src="/static/images/puc-logo.png" class="logo" alt="PUC">
                <h1>LEVEL TESTING RECEIPT</h1>
                <p>{timezone.now().strftime('%B %d, %Y %I:%M %p')}</p>
            </div>
            
            <div class="info">
                <div class="info-row">
                    <span>Name:</span>
                    <strong>{token.student_name}</strong>
                </div>
                <div class="info-row">
                    <span>Phone:</span>
                    <strong>{token.student_phone}</strong>
                </div>
                <div class="info-row">
                    <span>Amount:</span>
                    <strong>${token.payment_amount}</strong>
                </div>
                <div class="info-row">
                    <span>Receipt:</span>
                    <strong>#{token.receipt_number or token.id:06d}</strong>
                </div>
            </div>
            
            <div class="qr-code">
                <img src="data:image/png;base64,{qr_base64}" alt="QR Code">
            </div>
            
            <div class="access-code">
                {token.access_code}
            </div>
            
            <div class="footer">
                <p><strong>Important:</strong></p>
                <p>1. Scan QR code to start application</p>
                <p>2. Valid for 24 hours only</p>
                <p>3. Keep this receipt safe</p>
                <p>Thank you for choosing PUC!</p>
            </div>
        </body>
        </html>
        """
        
        return html
```

### 4.2 Telegram Bot Service

```python
# apps/level_testing/services/telegram_service.py

import asyncio
from telegram import Bot
from telegram.error import TelegramError
import logging

logger = logging.getLogger(__name__)

class TelegramBotService:
    """Service for Telegram bot integration."""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.bot = Bot(token=self.bot_token)
    
    def send_verification_code(self, phone: str, code: str, student_name: str) -> bool:
        """Send verification code to student via Telegram.
        
        Returns:
            True if sent successfully
        """
        try:
            # Find user by phone number
            # Note: This requires users to have shared their phone with the bot
            message = f"""
🔐 *PUC Level Testing Verification*

Hello {student_name}!

Your verification code is: *{code}*

This code will expire in 5 minutes.

Enter this code in the application to verify your Telegram.
            """
            
            # In production, you'd look up the user's Telegram ID by phone
            # For now, we'll send to a test channel
            asyncio.run(self._send_message(message))
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram verification: {e}")
            return False
    
    async def _send_message(self, text: str, chat_id: str = None):
        """Send message to Telegram."""
        if not chat_id:
            chat_id = settings.TELEGRAM_TEST_CHANNEL_ID
        
        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown'
        )
    
    def send_test_reminder(self, telegram_id: str, test_date, location: str):
        """Send test reminder to student."""
        message = f"""
📅 *Level Test Reminder*

Your test is tomorrow!

📍 Date: {test_date.strftime('%B %d, %Y')}
🕐 Time: {test_date.strftime('%I:%M %p')}
📍 Location: {location}

Please arrive 15 minutes early and bring:
• Valid ID
• Pen and pencil
• Water bottle (optional)

Good luck! 🍀
        """
        
        try:
            asyncio.run(self._send_message(message, telegram_id))
            return True
        except Exception as e:
            logger.error(f"Failed to send test reminder: {e}")
            return False
    
    def send_test_results(self, telegram_id: str, score: int, level: str):
        """Send test results to student."""
        message = f"""
🎉 *Test Results Available!*

Congratulations on completing your level test!

📊 Your Score: *{score}/100*
📚 Recommended Level: *{level}*

Next Steps:
1. Visit the registration office
2. Discuss your class schedule
3. Complete enrollment

We look forward to having you at PUC!

Questions? Reply to this message or call us.
        """
        
        try:
            asyncio.run(self._send_message(message, telegram_id))
            return True
        except Exception as e:
            logger.error(f"Failed to send test results: {e}")
            return False
```

## Step 5: URL Configuration

```python
# apps/level_testing/urls.py

from django.urls import path, include
from . import views

app_name = 'level_testing'

urlpatterns = [
    # Public token verification
    path('apply/<str:access_code>/', 
         views.TokenVerificationView.as_view(), 
         name='token_verify'),
    
    path('token/<str:access_code>/start/', 
         views.TokenVerificationView.as_view(), 
         name='token_start'),
    
    # Telegram integration
    path('telegram/', include([
        path('send-code/', 
             views.TelegramVerificationView.as_view(), 
             name='telegram_send_code'),
        path('verify/', 
             views.TelegramVerificationView.as_view(), 
             name='telegram_verify'),
    ])),
    
    # Application wizard
    path('wizard/', include([
        path('', views.WizardStartView.as_view(), name='wizard_start'),
        path('personal/', views.PersonalInfoStepView.as_view(), name='wizard_personal'),
        path('education/', views.EducationStepView.as_view(), name='wizard_education'),
        path('program/', views.ProgramStepView.as_view(), name='wizard_program'),
        path('review/', views.ReviewStepView.as_view(), name='wizard_review'),
        path('complete/', views.CompletionView.as_view(), name='wizard_complete'),
    ])),
    
    # API endpoints
    path('api/', include([
        path('save-progress/', 
             views.SaveProgressAPIView.as_view(), 
             name='api_save_progress'),
        path('verify-access/', 
             views.VerifyAccessAPIView.as_view(), 
             name='api_verify_access'),
    ])),
    
    # Staff/Cashier views
    path('cashier/', include([
        path('', 
             views.CashierDashboardView.as_view(), 
             name='cashier_dashboard'),
        path('collect-payment/', 
             views.CashierPaymentCollectionView.as_view(), 
             name='cashier_collect'),
        path('today-summary/', 
             views.CashierTodaySummaryView.as_view(), 
             name='cashier_summary'),
    ])),
    
    # Admin views
    path('admin/', include([
        path('tokens/', 
             views.TokenListView.as_view(), 
             name='admin_tokens'),
        path('applications/', 
             views.ApplicationListView.as_view(), 
             name='admin_applications'),
        path('reports/', 
             views.ReportsView.as_view(), 
             name='admin_reports'),
    ])),
]
```

## Step 6: Settings Configuration

```python
# config/settings/base.py

# Level Testing Configuration
LEVEL_TESTING_BASE_URL = env('LEVEL_TESTING_BASE_URL', default='https://apply.puc.edu.kh')
LEVEL_TESTING_TOKEN_EXPIRY_HOURS = 24
LEVEL_TESTING_DEFAULT_FEE = Decimal('5.00')
LEVEL_TESTING_ENABLE_TELEGRAM = env.bool('ENABLE_TELEGRAM', default=True)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_BOT_USERNAME = env('TELEGRAM_BOT_USERNAME', default='@PUCLevelTestBot')
TELEGRAM_TEST_CHANNEL_ID = env('TELEGRAM_TEST_CHANNEL', default='')
TELEGRAM_BOT_ENABLED = bool(TELEGRAM_BOT_TOKEN)

# QR Code Configuration
QR_CODE_VERSION = 1
QR_CODE_ERROR_CORRECTION = 'H'  # High error correction
QR_CODE_BOX_SIZE = 10
QR_CODE_BORDER = 4

# Thermal Printer Configuration (if using)
THERMAL_PRINTER_ENABLED = env.bool('THERMAL_PRINTER_ENABLED', default=False)
THERMAL_PRINTER_PORT = env('THERMAL_PRINTER_PORT', default='/dev/usb/lp0')
```

## Step 7: Deployment Checklist

### Pre-deployment
- [ ] Run database migrations
- [ ] Configure Telegram bot token
- [ ] Set up SSL certificate for HTTPS
- [ ] Configure CORS for mobile access
- [ ] Set up Redis for caching
- [ ] Configure email backend

### Testing
- [ ] Test payment collection flow
- [ ] Test QR code generation
- [ ] Test QR code scanning
- [ ] Test Telegram verification
- [ ] Test application wizard on mobile
- [ ] Test offline functionality
- [ ] Test auto-save feature
- [ ] Test token expiration

### Security
- [ ] Enable CSRF protection
- [ ] Configure rate limiting
- [ ] Set up SSL/TLS
- [ ] Validate all inputs
- [ ] Secure Telegram bot token
- [ ] Set up monitoring

### Training
- [ ] Train cashiers on payment collection
- [ ] Create user manual
- [ ] Document troubleshooting steps
- [ ] Set up support channel

## Conclusion

This implementation guide provides a complete blueprint for transforming the level testing system into a modern, payment-first, mobile-optimized application with Telegram integration. The system ensures only paid applicants can access the form while providing a seamless experience on mobile devices.