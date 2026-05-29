import pytest

from app.services.safe_wallet_service import SafeWalletService
from app.models.safe_wallet import SafeWallet, WithdrawalRecord


@pytest.fixture
def service():
    return SafeWalletService()


class TestGetOrCreateSafeWallet:
    @pytest.mark.asyncio
    async def test_creates_new_wallet(self, session):
        svc = SafeWalletService()
        wallet = await svc.get_or_create_safe_wallet(
            user_id="u-create",
            name="My USDC Wallet",
            currency="USDC",
            session=session,
        )
        assert wallet.id is not None
        assert wallet.user_id == "u-create"
        assert wallet.name == "My USDC Wallet"
        assert wallet.currency == "USDC"
        assert wallet.balance == 0.0

    @pytest.mark.asyncio
    async def test_returns_existing_wallet(self, session):
        svc = SafeWalletService()
        w1 = await svc.get_or_create_safe_wallet(
            user_id="u-existing",
            name="Savings",
            currency="USDC",
            session=session,
        )
        w2 = await svc.get_or_create_safe_wallet(
            user_id="u-existing",
            name="Savings",
            currency="USDC",
            session=session,
        )
        assert w1.id == w2.id

    @pytest.mark.asyncio
    async def test_different_names_create_different_wallets(self, session):
        svc = SafeWalletService()
        w1 = await svc.get_or_create_safe_wallet(
            user_id="u-multi", name="Wallet A", currency="USDC", session=session,
        )
        w2 = await svc.get_or_create_safe_wallet(
            user_id="u-multi", name="Wallet B", currency="USDC", session=session,
        )
        assert w1.id != w2.id

    @pytest.mark.asyncio
    async def test_different_currencies_create_different_wallets(self, session):
        svc = SafeWalletService()
        w1 = await svc.get_or_create_safe_wallet(
            user_id="u-diff", name="Safe", currency="USDC", session=session,
        )
        w2 = await svc.get_or_create_safe_wallet(
            user_id="u-diff", name="Safe", currency="USDT", session=session,
        )
        assert w1.id != w2.id


class TestTransferToSafeWallet:
    @pytest.mark.asyncio
    async def test_transfer_updates_balance(self, session):
        svc = SafeWalletService()
        await svc.get_or_create_safe_wallet(
            user_id="u-t1", name="Main", currency="USDC", session=session,
        )
        result = await svc.transfer_to_safe_wallet(
            user_id="u-t1",
            amount=150.0,
            currency="USDC",
            source="profits",
            trigger_type="auto",
            strategy_id="strat-1",
            session=session,
        )
        assert result["success"] is True
        assert result["amount"] == 150.0
        assert result["new_balance"] == 150.0
        assert result["currency"] == "USDC"
        assert result["record_id"] is not None

    @pytest.mark.asyncio
    async def test_transfer_accumulates_balance(self, session):
        svc = SafeWalletService()
        await svc.get_or_create_safe_wallet(
            user_id="u-t2", name="Main", currency="USDC", session=session,
        )
        r1 = await svc.transfer_to_safe_wallet(
            user_id="u-t2", amount=100.0, currency="USDC",
            source="profits", trigger_type="auto",
            strategy_id=None, session=session,
        )
        r2 = await svc.transfer_to_safe_wallet(
            user_id="u-t2", amount=50.0, currency="USDC",
            source="manual", trigger_type="manual",
            strategy_id=None, session=session,
        )
        assert r2["new_balance"] == 150.0

    @pytest.mark.asyncio
    async def test_transfer_rejects_non_positive_amount(self, session):
        svc = SafeWalletService()
        result = await svc.transfer_to_safe_wallet(
            user_id="u-t3", amount=0.0, currency="USDC",
            source="profits", trigger_type="auto",
            strategy_id=None, session=session,
        )
        assert result["success"] is False
        assert "positive" in result["error"]

    @pytest.mark.asyncio
    async def test_transfer_rejects_negative_amount(self, session):
        svc = SafeWalletService()
        result = await svc.transfer_to_safe_wallet(
            user_id="u-t4", amount=-50.0, currency="USDC",
            source="profits", trigger_type="auto",
            strategy_id=None, session=session,
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_transfer_creates_wallet_if_missing(self, session):
        svc = SafeWalletService()
        result = await svc.transfer_to_safe_wallet(
            user_id="u-new-wallet", amount=200.0, currency="USDC",
            source="profits", trigger_type="auto",
            strategy_id=None, session=session,
        )
        assert result["success"] is True
        assert result["new_balance"] == 200.0


class TestGetSafeWalletBalance:
    @pytest.mark.asyncio
    async def test_returns_empty_for_no_wallets(self, session):
        svc = SafeWalletService()
        result = await svc.get_safe_wallet_balance(
            user_id="u-empty", session=session,
        )
        assert result["total_wallets"] == 0
        assert result["balances_by_currency"] == {}
        assert result["total_usd_equivalent"] == 0.0
        assert result["wallets"] == []

    @pytest.mark.asyncio
    async def test_returns_single_wallet_balance(self, session):
        svc = SafeWalletService()
        await svc.get_or_create_safe_wallet(
            user_id="u-bal1", name="Main", currency="USDC", session=session,
        )
        await svc.transfer_to_safe_wallet(
            user_id="u-bal1", amount=500.0, currency="USDC",
            source="profits", trigger_type="auto",
            strategy_id=None, session=session,
        )
        result = await svc.get_safe_wallet_balance(
            user_id="u-bal1", session=session,
        )
        assert result["total_wallets"] == 1
        assert result["balances_by_currency"]["USDC"] == 500.0
        assert len(result["wallets"]) == 1
        assert result["wallets"][0]["balance"] == 500.0

    @pytest.mark.asyncio
    async def test_totals_usd_only(self, session):
        svc = SafeWalletService()
        await svc.get_or_create_safe_wallet(
            user_id="u-multi-bal", name="USD", currency="USDC", session=session,
        )
        await svc.get_or_create_safe_wallet(
            user_id="u-multi-bal", name="Euro", currency="EUR", session=session,
        )
        await svc.transfer_to_safe_wallet(
            user_id="u-multi-bal", amount=300.0, currency="USDC",
            source="profits", trigger_type="auto",
            strategy_id=None, session=session,
        )
        await svc.transfer_to_safe_wallet(
            user_id="u-multi-bal", amount=200.0, currency="EUR",
            source="profits", trigger_type="auto",
            strategy_id=None, session=session,
        )
        result = await svc.get_safe_wallet_balance(
            user_id="u-multi-bal", session=session,
        )
        assert result["total_wallets"] == 2
        assert result["balances_by_currency"]["USDC"] == 300.0
        assert result["balances_by_currency"]["EUR"] == 200.0
        assert result["total_usd_equivalent"] == 300.0

    @pytest.mark.asyncio
    async def test_wallet_list_includes_metadata(self, session):
        svc = SafeWalletService()
        wallet = await svc.get_or_create_safe_wallet(
            user_id="u-meta", name="Savings", currency="USDC", session=session,
        )
        result = await svc.get_safe_wallet_balance(
            user_id="u-meta", session=session,
        )
        w = result["wallets"][0]
        assert w["id"] == wallet.id
        assert w["name"] == "Savings"
        assert w["currency"] == "USDC"
        assert w["created_at"] is not None


class TestGetWithdrawalHistory:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_records(self, session):
        svc = SafeWalletService()
        history = await svc.get_withdrawal_history(
            user_id="u-no-history", session=session,
        )
        assert history == []

    @pytest.mark.asyncio
    async def test_returns_records_for_user(self, session):
        svc = SafeWalletService()
        await svc.get_or_create_safe_wallet(
            user_id="u-hist1", name="Main", currency="USDC", session=session,
        )
        await svc.transfer_to_safe_wallet(
            user_id="u-hist1", amount=100.0, currency="USDC",
            source="profits", trigger_type="auto",
            strategy_id="s1", session=session,
        )
        await svc.transfer_to_safe_wallet(
            user_id="u-hist1", amount=50.0, currency="USDC",
            source="manual", trigger_type="manual",
            strategy_id="s2", session=session,
        )
        history = await svc.get_withdrawal_history(
            user_id="u-hist1", session=session,
        )
        assert len(history) == 2
        amounts = {r["amount"] for r in history}
        assert amounts == {100.0, 50.0}

    @pytest.mark.asyncio
    async def test_records_include_expected_fields(self, session):
        svc = SafeWalletService()
        await svc.get_or_create_safe_wallet(
            user_id="u-fields", name="Main", currency="USDC", session=session,
        )
        await svc.transfer_to_safe_wallet(
            user_id="u-fields", amount=75.0, currency="USDC",
            source="profits", trigger_type="auto",
            strategy_id="strat-99", session=session,
        )
        history = await svc.get_withdrawal_history(
            user_id="u-fields", session=session,
        )
        r = history[0]
        assert r["amount"] == 75.0
        assert r["currency"] == "USDC"
        assert r["source"] == "profits"
        assert r["trigger_type"] == "auto"
        assert r["strategy_id"] == "strat-99"
        assert r["status"] == "completed"
        assert r["created_at"] is not None

    @pytest.mark.asyncio
    async def test_does_not_return_other_users_records(self, session):
        svc = SafeWalletService()
        await svc.get_or_create_safe_wallet(
            user_id="u-isolated-a", name="A", currency="USDC", session=session,
        )
        await svc.get_or_create_safe_wallet(
            user_id="u-isolated-b", name="B", currency="USDC", session=session,
        )
        await svc.transfer_to_safe_wallet(
            user_id="u-isolated-a", amount=100.0, currency="USDC",
            source="profits", trigger_type="auto",
            strategy_id=None, session=session,
        )
        await svc.transfer_to_safe_wallet(
            user_id="u-isolated-b", amount=200.0, currency="USDC",
            source="profits", trigger_type="auto",
            strategy_id=None, session=session,
        )
        hist_a = await svc.get_withdrawal_history(
            user_id="u-isolated-a", session=session,
        )
        hist_b = await svc.get_withdrawal_history(
            user_id="u-isolated-b", session=session,
        )
        assert len(hist_a) == 1
        assert hist_a[0]["amount"] == 100.0
        assert len(hist_b) == 1
        assert hist_b[0]["amount"] == 200.0
