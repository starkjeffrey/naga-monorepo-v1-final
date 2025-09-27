# Level Testing Application System Redesign

## Executive Summary

This document outlines a complete redesign of the level_testing app to implement a payment-first, mobile-optimized workflow with Telegram integration and QR code-based tracking. The new system streamlines the process while ensuring only paid applicants can access the application form.

## Current vs. New Process Flow

### Current Flow (Problems)
1. Student fills out application form first
2. Payment is requested after form completion
3. No Telegram integration
4. Not optimized for mobile
5. Inconsistent tracking

### New Flow (Solution)
1. **Initial Contact** → Student approaches desk/booth
2. **Payment Collection** → $5 fee paid to cashier
3. **QR Code Generation** → Receipt with unique QR code
4. **Telegram Verification** → Optional but encouraged
5. **Application Form** → Mobile-optimized wizard
6. **Test Scheduling** → Automated slot assignment
7. **Test Completion** → Results and enrollment guidance

## System Architecture

### 1. Payment-First Gateway System

```python
# New model structure
class TestAccessToken(AuditModel):
    """Pre-application payment token with QR code."""
    
    # Unique identifier (7-digit with Luhn check)
    access_code = models.CharField(max_length=7, unique=True, db_index=True)
    
    # Payment tracking
    payment_amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_method = models.CharField(max_length=20)
    payment_received_at = models.DateTimeField()
    cashier = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # QR Code data
    qr_code_url = models.URLField()
    qr_code_data = models.JSONField()
    
    # Student pre-registration
    student_name = models.CharField(max_length=100)
    student_phone = models.CharField(max_length=20)
    
    # Usage tracking
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    application = models.OneToOneField(
        'PotentialStudent', 
        null=True, 
        blank=True,
        on_delete=models.CASCADE
    )
    
    # Telegram integration
    telegram_id = models.CharField(max_length=50, blank=True)
    telegram_username = models.CharField(max_length=50, blank=True)
    telegram_verified = models.BooleanField(default=False)
    telegram_verification_code = models.CharField(max_length=6, blank=True)
    telegram_verified_at = models.DateTimeField(null=True, blank=True)
```

### 2. Mobile-First UI Components

#### A. QR Code Landing Page
```html
<!-- Mobile-optimized landing page -->
<div class="mobile-container">
    <div class="hero-section">
        <h1>Welcome to PUC Level Testing</h1>
        <div class="language-toggle">
            <button class="lang-en active">English</button>
            <button class="lang-km">ខ្មែរ</button>
        </div>
    </div>
    
    <!-- Access verification -->
    <div class="access-card">
        <p class="student-name">{{ token.student_name }}</p>
        <p class="access-status">✓ Payment Verified</p>
        
        <!-- Telegram integration prompt -->
        <div class="telegram-section">
            <h3>Connect Telegram (Optional)</h3>
            <p>Get test results and updates instantly</p>
            <button class="telegram-connect-btn">
                <i class="fab fa-telegram"></i> Connect Telegram
            </button>
        </div>
        
        <!-- Start application button -->
        <button class="start-application-btn">
            Start Application Form
        </button>
    </div>
</div>
```

#### B. Telegram Verification Flow
```python
class TelegramVerificationView(View):
    """Handle Telegram verification process."""
    
    def post(self, request, access_code):
        token = get_object_or_404(TestAccessToken, access_code=access_code)
        
        # Generate 6-digit verification code
        verification_code = generate_verification_code()
        token.telegram_verification_code = verification_code
        token.save()
        
        # Send code via Telegram bot
        telegram_service = TelegramService()
        telegram_service.send_verification_code(
            phone=token.student_phone,
            code=verification_code,
            student_name=token.student_name
        )
        
        return JsonResponse({
            'status': 'code_sent',
            'message': 'Check your Telegram for verification code'
        })
    
    def verify_code(self, request, access_code):
        token = get_object_or_404(TestAccessToken, access_code=access_code)
        submitted_code = request.POST.get('code')
        
        if token.telegram_verification_code == submitted_code:
            # Get Telegram user info from bot
            telegram_info = telegram_service.get_user_info(token.student_phone)
            
            token.telegram_id = telegram_info['id']
            token.telegram_username = telegram_info['username']
            token.telegram_verified = True
            token.telegram_verified_at = timezone.now()
            token.save()
            
            return JsonResponse({
                'status': 'verified',
                'telegram_username': telegram_info['username']
            })
        
        return JsonResponse({'status': 'invalid_code'}, status=400)
```

### 3. Mobile-Optimized Application Wizard

#### Progressive Web App Features
```javascript
// Service worker for offline capability
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open('level-testing-v1').then(cache => {
            return cache.addAll([
                '/level-testing/wizard/',
                '/static/css/mobile-wizard.css',
                '/static/js/wizard.js',
                '/static/images/logo.png'
            ]);
        })
    );
});

// Auto-save form progress
class ApplicationWizard {
    constructor(accessCode) {
        this.accessCode = accessCode;
        this.currentStep = 1;
        this.formData = {};
        this.initAutoSave();
    }
    
    initAutoSave() {
        // Save to localStorage every 30 seconds
        setInterval(() => {
            this.saveProgress();
        }, 30000);
        
        // Save on input change
        document.querySelectorAll('input, select, textarea').forEach(field => {
            field.addEventListener('change', () => this.saveProgress());
        });
    }
    
    saveProgress() {
        const data = {
            accessCode: this.accessCode,
            currentStep: this.currentStep,
            formData: this.collectFormData(),
            timestamp: new Date().toISOString()
        };
        
        // Save locally
        localStorage.setItem('level-testing-progress', JSON.stringify(data));
        
        // Sync to server if online
        if (navigator.onLine) {
            fetch('/api/level-testing/save-progress/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(data)
            });
        }
    }
}
```

### 4. QR Code Generation System

```python
class QRCodeService:
    """Service for generating and managing QR codes."""
    
    @staticmethod
    def generate_access_qr(token: TestAccessToken) -> tuple[str, bytes]:
        """Generate QR code for test access token.
        
        Returns:
            Tuple of (url, qr_code_image_bytes)
        """
        # Build URL with access code
        base_url = settings.LEVEL_TESTING_BASE_URL
        access_url = f"{base_url}/apply/{token.access_code}/"
        
        # Add query parameters
        params = {
            'name': token.student_name,
            'lang': 'en',  # Default language
            'ts': token.created_at.timestamp()
        }
        
        full_url = f"{access_url}?{urlencode(params)}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(full_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Add logo overlay
        logo = Image.open('static/images/puc-logo.png')
        logo = logo.resize((60, 60))
        
        # Position logo in center
        pos = ((img.size[0] - logo.size[0]) // 2,
               (img.size[1] - logo.size[1]) // 2)
        img.paste(logo, pos)
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        return full_url, buffer.getvalue()
```

### 5. Cashier Interface

```python
class CashierPaymentView(LoginRequiredMixin, FormView):
    """Quick payment collection interface for cashiers."""
    
    template_name = 'level_testing/cashier/collect_payment.html'
    form_class = QuickPaymentForm
    
    def form_valid(self, form):
        with transaction.atomic():
            # Create access token
            token = TestAccessToken.objects.create(
                student_name=form.cleaned_data['student_name'],
                student_phone=form.cleaned_data['student_phone'],
                payment_amount=form.cleaned_data['amount'],
                payment_method=form.cleaned_data['payment_method'],
                payment_received_at=timezone.now(),
                cashier=self.request.user
            )
            
            # Generate QR code
            qr_service = QRCodeService()
            url, qr_image = qr_service.generate_access_qr(token)
            
            # Save QR data
            token.qr_code_url = url
            token.qr_code_data = {
                'generated_at': timezone.now().isoformat(),
                'cashier_id': self.request.user.id,
                'terminal': self.request.META.get('REMOTE_ADDR')
            }
            token.save()
            
            # Print receipt with QR code
            if form.cleaned_data.get('print_receipt'):
                printer_service = ThermalPrinterService()
                printer_service.print_payment_receipt(token, qr_image)
            
            # Return success with QR code display
            return render(self.request, 'level_testing/cashier/payment_success.html', {
                'token': token,
                'qr_code_base64': base64.b64encode(qr_image).decode(),
                'print_sent': form.cleaned_data.get('print_receipt')
            })
```

### 6. Database Schema Updates

```sql
-- Add new tables
CREATE TABLE level_testing_testaccesstoken (
    id SERIAL PRIMARY KEY,
    access_code VARCHAR(7) UNIQUE NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    student_phone VARCHAR(20) NOT NULL,
    payment_amount DECIMAL(8,2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    payment_received_at TIMESTAMP NOT NULL,
    cashier_id INTEGER REFERENCES auth_user(id),
    qr_code_url TEXT,
    qr_code_data JSONB,
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    application_id INTEGER REFERENCES level_testing_potentialstudent(id),
    telegram_id VARCHAR(50),
    telegram_username VARCHAR(50),
    telegram_verified BOOLEAN DEFAULT FALSE,
    telegram_verification_code VARCHAR(6),
    telegram_verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_access_code ON level_testing_testaccesstoken(access_code);
CREATE INDEX idx_student_phone ON level_testing_testaccesstoken(student_phone);
CREATE INDEX idx_telegram_id ON level_testing_testaccesstoken(telegram_id);
CREATE INDEX idx_is_used ON level_testing_testaccesstoken(is_used);

-- Update existing tables
ALTER TABLE level_testing_potentialstudent 
ADD COLUMN access_token_id INTEGER REFERENCES level_testing_testaccesstoken(id),
ADD COLUMN telegram_id VARCHAR(50),
ADD COLUMN telegram_notifications_enabled BOOLEAN DEFAULT FALSE;
```

### 7. API Endpoints

```yaml
# RESTful API Design
endpoints:
  # Public endpoints (no auth required)
  - path: /api/v1/level-testing/verify-access/
    method: POST
    description: Verify access code and get token details
    request:
      access_code: string
    response:
      valid: boolean
      student_name: string
      payment_verified: boolean
      telegram_connected: boolean
      application_started: boolean
  
  # Telegram verification
  - path: /api/v1/level-testing/telegram/send-code/
    method: POST
    description: Send verification code via Telegram
    request:
      access_code: string
      phone_number: string
    response:
      status: sent|error
      message: string
  
  - path: /api/v1/level-testing/telegram/verify/
    method: POST
    description: Verify Telegram code
    request:
      access_code: string
      verification_code: string
    response:
      verified: boolean
      telegram_username: string
  
  # Application wizard
  - path: /api/v1/level-testing/application/start/
    method: POST
    description: Start application with valid token
    request:
      access_code: string
    response:
      application_id: string
      current_step: integer
      total_steps: integer
  
  - path: /api/v1/level-testing/application/save-progress/
    method: POST
    description: Auto-save application progress
    request:
      application_id: string
      current_step: integer
      form_data: object
    response:
      saved: boolean
      last_saved: timestamp
  
  # Cashier endpoints (auth required)
  - path: /api/v1/level-testing/cashier/collect-payment/
    method: POST
    description: Record payment and generate access token
    auth: required
    permission: level_testing.add_payment
    request:
      student_name: string
      student_phone: string
      amount: decimal
      payment_method: string
    response:
      access_code: string
      qr_code_url: string
      qr_code_image: base64
      receipt_number: string
```

### 8. Mobile-First CSS Framework

```scss
// Mobile-first responsive design
// Base styles for mobile devices

.mobile-container {
    width: 100%;
    max-width: 100vw;
    padding: 1rem;
    overflow-x: hidden;
}

// Card-based layout
.wizard-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    padding: 1.5rem;
    margin-bottom: 1rem;
    
    &__header {
        border-bottom: 2px solid #f0f0f0;
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
        
        h2 {
            font-size: 1.25rem;
            font-weight: 600;
            color: #333;
            margin: 0;
        }
        
        .step-indicator {
            display: flex;
            align-items: center;
            margin-top: 0.5rem;
            font-size: 0.875rem;
            color: #666;
            
            .current-step {
                font-weight: 600;
                color: #4A90E2;
            }
        }
    }
    
    &__body {
        .form-group {
            margin-bottom: 1.5rem;
            
            label {
                display: block;
                font-size: 0.875rem;
                font-weight: 500;
                color: #555;
                margin-bottom: 0.5rem;
                
                &.required::after {
                    content: ' *';
                    color: #E74C3C;
                }
            }
            
            input, select, textarea {
                width: 100%;
                padding: 0.75rem;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 1rem;
                transition: border-color 0.2s;
                
                &:focus {
                    outline: none;
                    border-color: #4A90E2;
                    box-shadow: 0 0 0 3px rgba(74,144,226,0.1);
                }
                
                &.error {
                    border-color: #E74C3C;
                }
            }
            
            .help-text {
                font-size: 0.75rem;
                color: #999;
                margin-top: 0.25rem;
            }
            
            .error-message {
                font-size: 0.75rem;
                color: #E74C3C;
                margin-top: 0.25rem;
            }
        }
    }
    
    &__footer {
        display: flex;
        justify-content: space-between;
        padding-top: 1.5rem;
        border-top: 1px solid #f0f0f0;
        
        .btn {
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 500;
            font-size: 1rem;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
            
            &--primary {
                background: #4A90E2;
                color: white;
                
                &:hover {
                    background: #357ABD;
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(74,144,226,0.3);
                }
            }
            
            &--secondary {
                background: #f0f0f0;
                color: #666;
                
                &:hover {
                    background: #e0e0e0;
                }
            }
            
            &:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
        }
    }
}

// Progress bar
.progress-bar {
    width: 100%;
    height: 4px;
    background: #f0f0f0;
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 2rem;
    
    &__fill {
        height: 100%;
        background: linear-gradient(90deg, #4A90E2, #357ABD);
        transition: width 0.3s ease;
    }
}

// Telegram integration styles
.telegram-section {
    background: linear-gradient(135deg, #0088cc, #0077b5);
    color: white;
    padding: 1.5rem;
    border-radius: 12px;
    text-align: center;
    margin: 1.5rem 0;
    
    h3 {
        margin: 0 0 0.5rem;
        font-size: 1.125rem;
    }
    
    p {
        margin: 0 0 1rem;
        opacity: 0.9;
        font-size: 0.875rem;
    }
    
    .telegram-connect-btn {
        background: white;
        color: #0088cc;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        transition: transform 0.2s;
        
        &:hover {
            transform: scale(1.05);
        }
        
        i {
            font-size: 1.25rem;
        }
    }
}

// Responsive breakpoints
@media (min-width: 768px) {
    .mobile-container {
        max-width: 600px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    .wizard-card {
        padding: 2rem;
        
        &__header h2 {
            font-size: 1.5rem;
        }
    }
}

@media (min-width: 1024px) {
    .mobile-container {
        max-width: 800px;
    }
}
```

### 9. Telegram Bot Integration

```python
# telegram_bot.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

class LevelTestingBot:
    """Telegram bot for level testing integration."""
    
    def __init__(self, token: str):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup command and message handlers."""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("verify", self.verify_command))
        self.app.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context):
        """Handle /start command."""
        keyboard = [
            [InlineKeyboardButton("🔐 Verify for Level Testing", callback_data='verify')],
            [InlineKeyboardButton("📱 Share Contact", callback_data='share_contact')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "🎓 *Welcome to PUC Level Testing Bot!*\n\n"
            "I can help you:\n"
            "• Verify your identity for the level test\n"
            "• Receive test results and updates\n"
            "• Get reminders about your test schedule\n\n"
            "Please choose an option below:"
        )
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def verify_command(self, update: Update, context):
        """Handle verification process."""
        # Check if user has shared contact
        user_id = update.effective_user.id
        phone = self.get_user_phone(user_id)
        
        if not phone:
            # Request contact sharing
            keyboard = [[KeyboardButton("📱 Share Contact", request_contact=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            
            await update.message.reply_text(
                "To verify your identity, please share your contact:",
                reply_markup=reply_markup
            )
            return
        
        # Check if phone is registered
        token = self.find_token_by_phone(phone)
        
        if token:
            # Send verification code
            code = self.generate_verification_code()
            self.save_verification_code(token, code)
            
            message = (
                f"🔐 *Verification Code*\n\n"
                f"Your code is: `{code}`\n\n"
                f"Enter this code in the level testing application to verify your Telegram."
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ No level testing application found for your phone number.\n"
                "Please complete payment at the registration desk first."
            )
    
    async def send_test_reminder(self, telegram_id: str, test_date: datetime, location: str):
        """Send test reminder to student."""
        message = (
            f"📅 *Level Test Reminder*\n\n"
            f"Your test is scheduled for:\n"
            f"📍 Date: {test_date.strftime('%B %d, %Y')}\n"
            f"🕐 Time: {test_date.strftime('%I:%M %p')}\n"
            f"📍 Location: {location}\n\n"
            f"Please arrive 15 minutes early.\n"
            f"Don't forget to bring your ID!"
        )
        
        await self.app.bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode='Markdown'
        )
    
    async def send_test_results(self, telegram_id: str, score: int, level: str):
        """Send test results to student."""
        message = (
            f"🎉 *Test Results Available!*\n\n"
            f"Score: {score}/100\n"
            f"Recommended Level: {level}\n\n"
            f"Please visit the registration office to discuss your enrollment options.\n\n"
            f"Thank you for choosing PUC!"
        )
        
        await self.app.bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode='Markdown'
        )
```

### 10. Implementation Timeline

#### Phase 1: Foundation (Week 1-2)
- [ ] Create TestAccessToken model
- [ ] Build cashier payment interface
- [ ] Implement QR code generation
- [ ] Set up basic mobile landing page

#### Phase 2: Telegram Integration (Week 3)
- [ ] Deploy Telegram bot
- [ ] Implement verification flow
- [ ] Add phone number validation
- [ ] Test notification system

#### Phase 3: Mobile Application (Week 4-5)
- [ ] Convert wizard to mobile-first design
- [ ] Implement offline capability
- [ ] Add auto-save functionality
- [ ] Optimize for slow connections

#### Phase 4: Testing & Refinement (Week 6)
- [ ] User acceptance testing
- [ ] Performance optimization
- [ ] Security audit
- [ ] Staff training

## Security Considerations

1. **Access Code Security**
   - 7-digit codes with Luhn check digit
   - One-time use only
   - 24-hour expiration
   - Rate limiting on verification attempts

2. **Telegram Verification**
   - 6-digit OTP with 5-minute expiry
   - Maximum 3 attempts
   - Phone number validation
   - Bot token encryption

3. **Data Protection**
   - HTTPS only
   - CSRF protection
   - Input sanitization
   - SQL injection prevention
   - XSS protection

4. **Payment Security**
   - Audit trail for all transactions
   - Cashier authentication required
   - Daily reconciliation reports
   - Duplicate payment detection

## Performance Optimization

1. **Mobile Optimization**
   - Lazy loading for images
   - Service worker caching
   - Minified CSS/JS
   - Progressive enhancement

2. **Database Optimization**
   - Indexed access_code field
   - Indexed phone numbers
   - Query optimization
   - Connection pooling

3. **Caching Strategy**
   - Redis for session data
   - CDN for static assets
   - Browser caching headers
   - API response caching

## Monitoring & Analytics

1. **Key Metrics**
   - Payment to application conversion rate
   - Telegram verification adoption rate
   - Average form completion time
   - Drop-off points in wizard
   - Test scheduling efficiency

2. **Error Tracking**
   - Sentry integration
   - Custom error logging
   - Failed payment alerts
   - QR code scan failures

3. **Usage Analytics**
   - Google Analytics 4
   - Custom event tracking
   - Funnel analysis
   - Device/browser stats

## Conclusion

This redesign transforms the level testing application into a modern, mobile-first system with robust payment verification and optional Telegram integration. The payment-first approach ensures only serious applicants proceed, while the mobile optimization and offline capabilities provide a seamless experience for students applying on their phones.

The QR code system provides a secure, trackable link between payment and application, while the Telegram integration offers a modern communication channel for test updates and results.