"""Tests for General Ledger models in the finance app.

Tests the new G/L integration models including:
- GLAccount: Chart of accounts
- FeeGLMapping: Fee to G/L account mappings
- JournalEntry: Journal entries for bookkeeping
- JournalEntryLine: Individual journal entry lines
- GLBatch: Batch processing for journal entries
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.finance.models import (
    FeeGLMapping,
    FeeType,
    GLAccount,
    GLBatch,
    JournalEntry,
    JournalEntryLine,
)

User = get_user_model()


class GLAccountModelTest(TestCase):
    """Test GLAccount model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
        )

    def test_create_gl_account(self):
        """Test creating a G/L account."""
        account = GLAccount.objects.create(
            account_code="4000",
            account_name="Tuition Revenue",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
            is_active=True,
            description="Revenue from tuition fees",
        )

        assert account.account_code == "4000"
        assert account.account_name == "Tuition Revenue"
        assert account.account_type == GLAccount.AccountType.REVENUE
        assert str(account) == "4000 - Tuition Revenue"

    def test_hierarchical_accounts(self):
        """Test parent-child account relationships."""
        parent = GLAccount.objects.create(
            account_code="4000",
            account_name="Revenue",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
        )

        child = GLAccount.objects.create(
            account_code="4100",
            account_name="Tuition Revenue",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
            parent_account=parent,
        )

        assert child.parent_account == parent
        assert child.full_account_path == "Revenue > Tuition Revenue"

    def test_account_code_validation(self):
        """Test account code format validation."""
        account = GLAccount(
            account_code="4000-TEST",  # Valid: alphanumeric with hyphens
            account_name="Test Account",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
        )
        account.full_clean()  # Should not raise

        # Test invalid characters
        account.account_code = "4000@TEST"  # Invalid: contains @
        with pytest.raises(ValidationError) as exc_info:
            account.full_clean()
        assert "Account code must contain only letters" in str(exc_info.value)

    def test_circular_parent_prevention(self):
        """Test prevention of circular parent references."""
        account = GLAccount.objects.create(
            account_code="4000",
            account_name="Revenue",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
        )

        account.parent_account = account
        with pytest.raises(ValidationError) as exc_info:
            account.full_clean()
        assert "Account cannot be its own parent" in str(exc_info.value)


class FeeGLMappingModelTest(TestCase):
    """Test FeeGLMapping model functionality."""

    def setUp(self):
        """Set up test data."""
        self.revenue_account = GLAccount.objects.create(
            account_code="4100",
            account_name="Test Fee Revenue",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
        )

        self.receivable_account = GLAccount.objects.create(
            account_code="1200",
            account_name="Accounts Receivable",
            account_type=GLAccount.AccountType.ASSET,
            account_category=GLAccount.AccountCategory.CURRENT_ASSET,
        )

    def test_create_fee_mapping(self):
        """Test creating a fee to G/L mapping."""
        mapping = FeeGLMapping.objects.create(
            fee_type=FeeType.APPLICATION,
            fee_code="LT_PLACEMENT",
            revenue_account=self.revenue_account,
            receivable_account=self.receivable_account,
            effective_date=date(2025, 1, 1),
        )

        assert mapping.fee_code == "LT_PLACEMENT"
        assert mapping.revenue_account == self.revenue_account
        assert mapping.is_active  # Should be active for current date
        assert str(mapping) == "LT_PLACEMENT → 4100"

    def test_mapping_date_validation(self):
        """Test effective/end date validation."""
        mapping = FeeGLMapping(
            fee_type=FeeType.APPLICATION,
            fee_code="TEST_FEE",
            revenue_account=self.revenue_account,
            effective_date=date(2025, 1, 1),
            end_date=date(2024, 12, 31),  # End before start
        )

        with pytest.raises(ValidationError) as exc_info:
            mapping.full_clean()
        assert "End date must be after effective date" in str(exc_info.value)

    def test_revenue_account_type_validation(self):
        """Test that revenue account must be of type REVENUE."""
        expense_account = GLAccount.objects.create(
            account_code="6000",
            account_name="Test Expense",
            account_type=GLAccount.AccountType.EXPENSE,
            account_category=GLAccount.AccountCategory.OPERATING_EXPENSE,
        )

        mapping = FeeGLMapping(
            fee_type=FeeType.APPLICATION,
            fee_code="TEST_FEE",
            revenue_account=expense_account,  # Wrong type
            effective_date=date(2025, 1, 1),
        )

        with pytest.raises(ValidationError) as exc_info:
            mapping.full_clean()
        assert "Revenue account must be of type 'Revenue'" in str(exc_info.value)


class JournalEntryModelTest(TestCase):
    """Test JournalEntry model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="accountant@test.com",
            password="testpass123",
        )

        self.cash_account = GLAccount.objects.create(
            account_code="1010",
            account_name="Cash on Hand",
            account_type=GLAccount.AccountType.ASSET,
            account_category=GLAccount.AccountCategory.CURRENT_ASSET,
        )

        self.revenue_account = GLAccount.objects.create(
            account_code="4000",
            account_name="Tuition Revenue",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
        )

    def test_create_journal_entry(self):
        """Test creating a journal entry."""
        entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-001",
            entry_date=date(2025, 1, 15),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Daily cash receipts",
            prepared_by=self.user,
        )

        assert entry.entry_number == "JE-2025-01-001"
        assert entry.status == JournalEntry.EntryStatus.DRAFT
        assert not entry.is_balanced  # No lines yet
        assert str(entry) == "JE-2025-01-001 - Daily cash receipts"

    def test_accounting_period_format_validation(self):
        """Test accounting period format validation."""
        entry = JournalEntry(
            entry_number="JE-TEST-001",
            entry_date=date(2025, 1, 15),
            accounting_period="2025/01",  # Wrong format
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Test entry",
            prepared_by=self.user,
        )

        with pytest.raises(ValidationError) as exc_info:
            entry.full_clean()
        assert "Accounting period must be in YYYY-MM format" in str(exc_info.value)

    def test_entry_date_period_validation(self):
        """Test that entry date must be within accounting period."""
        entry = JournalEntry(
            entry_number="JE-TEST-001",
            entry_date=date(2025, 2, 15),  # February
            accounting_period="2025-01",  # January
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Test entry",
            prepared_by=self.user,
        )

        with pytest.raises(ValidationError) as exc_info:
            entry.full_clean()
        assert "Entry date must be within the specified accounting period" in str(exc_info.value)

    def test_balanced_journal_entry(self):
        """Test creating a balanced journal entry with lines."""
        entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-002",
            entry_date=date(2025, 1, 15),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Tuition payment received",
            prepared_by=self.user,
        )

        # Create debit line
        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=1,
            gl_account=self.cash_account,
            debit_amount=Decimal("1000.00"),
            credit_amount=Decimal("0.00"),
            description="Cash received",
        )

        # Create credit line
        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=2,
            gl_account=self.revenue_account,
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("1000.00"),
            description="Tuition revenue",
        )

        # Calculate totals
        entry.calculate_totals()
        entry.refresh_from_db()

        assert entry.total_debits == Decimal("1000.00")
        assert entry.total_credits == Decimal("1000.00")
        assert entry.is_balanced
        assert entry.balance_amount == Decimal("0.00")

    def test_approve_journal_entry(self):
        """Test approving a journal entry."""
        entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-003",
            entry_date=date(2025, 1, 15),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Test approval",
            prepared_by=self.user,
            total_debits=Decimal("500.00"),
            total_credits=Decimal("500.00"),
        )

        # Approve the entry
        entry.approve(self.user)
        entry.refresh_from_db()

        assert entry.status == JournalEntry.EntryStatus.APPROVED
        assert entry.approved_by == self.user
        assert entry.approved_date is not None

    def test_cannot_approve_unbalanced_entry(self):
        """Test that unbalanced entries cannot be approved."""
        entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-004",
            entry_date=date(2025, 1, 15),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Unbalanced entry",
            prepared_by=self.user,
            total_debits=Decimal("500.00"),
            total_credits=Decimal("400.00"),  # Unbalanced
        )

        with pytest.raises(ValidationError) as exc_info:
            entry.approve(self.user)
        assert "Cannot approve unbalanced journal entry" in str(exc_info.value)

    def test_post_to_gl(self):
        """Test posting an approved entry to G/L."""
        entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-005",
            entry_date=date(2025, 1, 15),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Test posting",
            prepared_by=self.user,
            total_debits=Decimal("500.00"),
            total_credits=Decimal("500.00"),
            status=JournalEntry.EntryStatus.APPROVED,
            approved_by=self.user,
            approved_date=timezone.now(),
        )

        entry.post_to_gl()
        entry.refresh_from_db()

        assert entry.status == JournalEntry.EntryStatus.POSTED
        assert entry.posted_date is not None

    def test_cannot_post_unapproved_entry(self):
        """Test that only approved entries can be posted."""
        entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-006",
            entry_date=date(2025, 1, 15),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Unapproved entry",
            prepared_by=self.user,
            status=JournalEntry.EntryStatus.DRAFT,
        )

        with pytest.raises(ValidationError) as exc_info:
            entry.post_to_gl()
        assert "Only approved entries can be posted to G/L" in str(exc_info.value)


class JournalEntryLineModelTest(TestCase):
    """Test JournalEntryLine model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="accountant@test.com",
            password="testpass123",
        )

        self.account = GLAccount.objects.create(
            account_code="1010",
            account_name="Cash",
            account_type=GLAccount.AccountType.ASSET,
            account_category=GLAccount.AccountCategory.CURRENT_ASSET,
        )

        self.dept_account = GLAccount.objects.create(
            account_code="6000",
            account_name="Department Expense",
            account_type=GLAccount.AccountType.EXPENSE,
            account_category=GLAccount.AccountCategory.OPERATING_EXPENSE,
            requires_department=True,
        )

        self.entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-001",
            entry_date=date(2025, 1, 15),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Test entry",
            prepared_by=self.user,
        )

    def test_create_debit_line(self):
        """Test creating a debit journal entry line."""
        line = JournalEntryLine.objects.create(
            journal_entry=self.entry,
            line_number=1,
            gl_account=self.account,
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("0.00"),
            description="Debit cash",
        )

        assert line.debit_amount == Decimal("100.00")
        assert line.credit_amount == Decimal("0.00")
        assert str(line) == "Dr 1010 100.00"

    def test_create_credit_line(self):
        """Test creating a credit journal entry line."""
        line = JournalEntryLine.objects.create(
            journal_entry=self.entry,
            line_number=2,
            gl_account=self.account,
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("100.00"),
            description="Credit cash",
        )

        assert line.debit_amount == Decimal("0.00")
        assert line.credit_amount == Decimal("100.00")
        assert str(line) == "Cr 1010 100.00"

    def test_cannot_have_both_debit_and_credit(self):
        """Test that a line cannot have both debit and credit amounts."""
        line = JournalEntryLine(
            journal_entry=self.entry,
            line_number=1,
            gl_account=self.account,
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("100.00"),  # Both set
            description="Invalid line",
        )

        with pytest.raises(ValidationError) as exc_info:
            line.full_clean()
        assert "A line can have either debit or credit amount, not both" in str(exc_info.value)

    def test_must_have_either_debit_or_credit(self):
        """Test that a line must have either debit or credit amount."""
        line = JournalEntryLine(
            journal_entry=self.entry,
            line_number=1,
            gl_account=self.account,
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("0.00"),  # Neither set
            description="Invalid line",
        )

        with pytest.raises(ValidationError) as exc_info:
            line.full_clean()
        assert "Either debit or credit amount must be greater than zero" in str(exc_info.value)

    def test_department_requirement(self):
        """Test department code requirement for certain accounts."""
        line = JournalEntryLine(
            journal_entry=self.entry,
            line_number=1,
            gl_account=self.dept_account,  # Requires department
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("0.00"),
            description="Department expense",
            # department_code missing
        )

        with pytest.raises(ValidationError) as exc_info:
            line.full_clean()
        assert "Department code is required for this G/L account" in str(exc_info.value)

        # Should work with department code
        line.department_code = "ADMIN"
        line.full_clean()  # Should not raise


class GLBatchModelTest(TestCase):
    """Test GLBatch model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
        )

    def test_create_gl_batch(self):
        """Test creating a G/L batch."""
        batch = GLBatch.objects.create(
            batch_number="GL-2025-01-001",
            accounting_period="2025-01",
            status=GLBatch.BatchStatus.PENDING,
        )

        assert batch.batch_number == "GL-2025-01-001"
        assert batch.status == GLBatch.BatchStatus.PENDING
        assert batch.total_entries == 0
        assert batch.total_amount == Decimal("0.00")
        assert str(batch) == "Batch GL-2025-01-001 - 2025-01"

    def test_add_journal_entry_to_batch(self):
        """Test adding journal entries to a batch."""
        batch = GLBatch.objects.create(
            batch_number="GL-2025-01-002",
            accounting_period="2025-01",
        )

        entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-001",
            entry_date=date(2025, 1, 15),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Test entry",
            prepared_by=self.user,
            total_debits=Decimal("1000.00"),
            total_credits=Decimal("1000.00"),
        )

        batch.add_journal_entry(entry)
        batch.refresh_from_db()

        assert batch.total_entries == 1
        assert batch.total_amount == Decimal("1000.00")

        # Verify entry has batch ID
        entry.refresh_from_db()
        assert entry.batch_id == batch.batch_number
