"""
BADMINTON.AI - MOMO PAYMENT GATEWAY ADAPTER (PHASE 7.4B)
Implements MoMo Collection Link / payWithMethod flow according to official MoMo v3 specifications:
- Official Request Canonicalization:
  accessKey=$accessKey&amount=$amount&extraData=$extraData&ipnUrl=$ipnUrl&orderId=$orderId&orderInfo=$orderInfo&partnerCode=$partnerCode&redirectUrl=$redirectUrl&requestId=$requestId&requestType=$requestType
- Official IPN Verification Canonicalization:
  accessKey=$accessKey&amount=$amount&extraData=$extraData&message=$message&orderId=$orderId&orderInfo=$orderInfo&orderType=$orderType&partnerCode=$partnerCode&payType=$payType&requestId=$requestId&responseTime=$responseTime&resultCode=$resultCode&transId=$transId
- Amount Constraint: 1,000 VND to 50,000,000 VND.
- Strict Fail-Closed / Sandbox Environment Protection.
"""

import os
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from decimal import Decimal

import httpx

from app.config import settings

logger = logging.getLogger("momo_adapter")

MIN_MOMO_AMOUNT = Decimal("1000")
MAX_MOMO_AMOUNT = Decimal("50000000")
DEFAULT_MOMO_TIMEOUT_SECONDS: float = 30.0
MIN_MOMO_TIMEOUT_SECONDS: float = 30.0


class MoMoPaymentAdapter:
    """
    Dedicated MoMo Payment Gateway Adapter (payWithMethod flow).
    Adheres strictly to official MoMo v3 API specifications:
    - Collection Link / payWithMethod hosted checkout
    - HMAC-SHA256 request signature
    - HMAC-SHA256 IPN verification
    - Integer VND monetary constraints [1,000, 50,000,000]
    - Strict sandbox-first / fail-closed security.
    """

    @property
    def provider_name(self) -> str:
        return "MOMO"

    def is_configured(self) -> bool:
        """
        Validates presence of all required credentials and settings.
        Returns False if any required key is missing or blank.
        """
        partner_code = os.getenv("MOMO_PARTNER_CODE") or getattr(settings, "MOMO_PARTNER_CODE", None)
        access_key = os.getenv("MOMO_ACCESS_KEY") or getattr(settings, "MOMO_ACCESS_KEY", None)
        secret_key = os.getenv("MOMO_SECRET_KEY") or getattr(settings, "MOMO_SECRET_KEY", None)
        redirect_url = os.getenv("MOMO_REDIRECT_URL") or getattr(settings, "MOMO_REDIRECT_URL", None)
        ipn_url = os.getenv("MOMO_IPN_URL") or getattr(settings, "MOMO_IPN_URL", None)

        if not all([partner_code, access_key, secret_key, redirect_url, ipn_url]):
            return False

        # Must not be placeholders
        if any(str(v).strip().startswith("your_") for v in [partner_code, access_key, secret_key]):
            return False

        return True

    def check_preflight(self) -> dict:
        """
        Phase 11.1 Preflight Gate:
        Evaluates environment readiness for Live MoMo Sandbox execution.
        Categorizes variables into CONFIGURED, MISSING, or INVALID.
        Enforces:
        - fail-closed security
        - sandbox-only endpoint
        - HTTPS public URLs for redirect and IPN (no localhost, no example.com)
        - timeout >= 30.0s
        - no secrets disclosed in return dictionary.
        """
        env_vars = {
            "MOMO_ENVIRONMENT": os.getenv("MOMO_ENVIRONMENT") or getattr(settings, "MOMO_ENVIRONMENT", None),
            "MOMO_PARTNER_CODE": os.getenv("MOMO_PARTNER_CODE") or getattr(settings, "MOMO_PARTNER_CODE", None),
            "MOMO_ACCESS_KEY": os.getenv("MOMO_ACCESS_KEY") or getattr(settings, "MOMO_ACCESS_KEY", None),
            "MOMO_SECRET_KEY": os.getenv("MOMO_SECRET_KEY") or getattr(settings, "MOMO_SECRET_KEY", None),
            "MOMO_ENDPOINT": os.getenv("MOMO_ENDPOINT") or getattr(settings, "MOMO_ENDPOINT", "https://test-payment.momo.vn"),
            "MOMO_REDIRECT_URL": os.getenv("MOMO_REDIRECT_URL") or getattr(settings, "MOMO_REDIRECT_URL", None),
            "MOMO_IPN_URL": os.getenv("MOMO_IPN_URL") or getattr(settings, "MOMO_IPN_URL", None),
            "MOMO_TIMEOUT_SECONDS": os.getenv("MOMO_TIMEOUT_SECONDS") or getattr(settings, "MOMO_TIMEOUT_SECONDS", DEFAULT_MOMO_TIMEOUT_SECONDS)
        }

        details = {}
        missing_vars = []
        invalid_vars = []

        # 1. MOMO_ENVIRONMENT
        raw_env = env_vars["MOMO_ENVIRONMENT"]
        if not raw_env or not str(raw_env).strip():
            details["MOMO_ENVIRONMENT"] = {"status": "MISSING", "reason": "Biến chưa được định nghĩa."}
            missing_vars.append("MOMO_ENVIRONMENT")
        else:
            val_env = str(raw_env).strip().lower()
            if val_env in ("production", "prod", "live"):
                details["MOMO_ENVIRONMENT"] = {"status": "INVALID", "reason": "Production environment strictly blocked."}
                invalid_vars.append("MOMO_ENVIRONMENT")
            elif val_env in ("sandbox", "test", "testing", "development", "local"):
                details["MOMO_ENVIRONMENT"] = {"status": "CONFIGURED", "reason": "Sandbox/test environment accepted."}
            else:
                details["MOMO_ENVIRONMENT"] = {"status": "INVALID", "reason": f"Môi trường không xác định: {val_env}"}
                invalid_vars.append("MOMO_ENVIRONMENT")

        # 2. MOMO_PARTNER_CODE, MOMO_ACCESS_KEY, MOMO_SECRET_KEY
        for sec_var in ["MOMO_PARTNER_CODE", "MOMO_ACCESS_KEY", "MOMO_SECRET_KEY"]:
            raw_val = env_vars[sec_var]
            if not raw_val or not str(raw_val).strip():
                details[sec_var] = {"status": "MISSING", "reason": "Biến chưa được thiết lập."}
                missing_vars.append(sec_var)
            else:
                str_val = str(raw_val).strip()
                if str_val.startswith("your_") or str_val.startswith("mock_") or "placeholder" in str_val.lower():
                    details[sec_var] = {"status": "INVALID", "reason": "Placeholder hoặc mock credential không được dùng cho Live Sandbox."}
                    invalid_vars.append(sec_var)
                elif len(str_val) < 4:
                    details[sec_var] = {"status": "INVALID", "reason": "Độ dài credential không hợp lệ."}
                    invalid_vars.append(sec_var)
                else:
                    details[sec_var] = {"status": "CONFIGURED", "reason": "Đã cấu hình hợp lệ."}

        # 3. MOMO_ENDPOINT
        raw_ep = env_vars["MOMO_ENDPOINT"]
        if not raw_ep or not str(raw_ep).strip():
            details["MOMO_ENDPOINT"] = {"status": "MISSING", "reason": "Endpoint chưa được cấu hình."}
            missing_vars.append("MOMO_ENDPOINT")
        else:
            str_ep = str(raw_ep).strip().lower()
            if "production" in str_ep or ("momo.vn/v2/gateway/api/create" in str_ep and "sandbox" not in str_ep and "test" not in str_ep):
                details["MOMO_ENDPOINT"] = {"status": "INVALID", "reason": "Endpoint trỏ tới production bị chặn hoàn toàn."}
                invalid_vars.append("MOMO_ENDPOINT")
            elif str_ep.startswith("https://test-payment.momo.vn") or "sandbox" in str_ep or "test" in str_ep:
                details["MOMO_ENDPOINT"] = {"status": "CONFIGURED", "reason": "Sandbox endpoint hợp lệ."}
            else:
                details["MOMO_ENDPOINT"] = {"status": "INVALID", "reason": "Endpoint không thuộc Sandbox MoMo."}
                invalid_vars.append("MOMO_ENDPOINT")

        # 4. MOMO_REDIRECT_URL & MOMO_IPN_URL
        for url_var in ["MOMO_REDIRECT_URL", "MOMO_IPN_URL"]:
            raw_url = env_vars[url_var]
            if not raw_url or not str(raw_url).strip():
                details[url_var] = {"status": "MISSING", "reason": "URL chưa được thiết lập."}
                missing_vars.append(url_var)
            else:
                str_url = str(raw_url).strip().lower()
                if not str_url.startswith("https://"):
                    details[url_var] = {"status": "INVALID", "reason": "Bắt buộc phải là giao thức HTTPS công khai."}
                    invalid_vars.append(url_var)
                elif "localhost" in str_url or "127.0.0.1" in str_url or "example.com" in str_url:
                    details[url_var] = {"status": "INVALID", "reason": "Không chấp nhận localhost, 127.0.0.1 hoặc domain giả định."}
                    invalid_vars.append(url_var)
                else:
                    details[url_var] = {"status": "CONFIGURED", "reason": "Public HTTPS URL hợp lệ."}

        # 5. MOMO_TIMEOUT_SECONDS
        raw_timeout = env_vars["MOMO_TIMEOUT_SECONDS"]
        try:
            val_timeout = float(raw_timeout)
            if val_timeout < MIN_MOMO_TIMEOUT_SECONDS:
                details["MOMO_TIMEOUT_SECONDS"] = {
                    "status": "INVALID",
                    "reason": f"Timeout {val_timeout}s thấp hơn ngưỡng tối thiểu {MIN_MOMO_TIMEOUT_SECONDS}s."
                }
                invalid_vars.append("MOMO_TIMEOUT_SECONDS")
            else:
                details["MOMO_TIMEOUT_SECONDS"] = {
                    "status": "CONFIGURED",
                    "reason": f"Timeout {val_timeout}s hợp lệ."
                }
        except (ValueError, TypeError):
            details["MOMO_TIMEOUT_SECONDS"] = {"status": "INVALID", "reason": "Giá trị timeout không phải số hợp lệ."}
            invalid_vars.append("MOMO_TIMEOUT_SECONDS")

        gate_status = "PASS" if not missing_vars and not invalid_vars else "BLOCKED — PREFLIGHT FAILED"

        return {
            "status": gate_status,
            "details": details,
            "missing_variables": missing_vars,
            "invalid_variables": invalid_vars
        }

    def is_production_blocked(self) -> bool:
        """
        Phase 7.4B Requirement: Production environment is strictly blocked.
        Only 'sandbox' or 'test' environments are permitted.
        """
        momo_env = (os.getenv("MOMO_ENVIRONMENT") or getattr(settings, "MOMO_ENVIRONMENT", "sandbox")).strip().lower()
        sys_env = (os.getenv("ENVIRONMENT") or getattr(settings, "ENVIRONMENT", "")).strip().lower()
        node_env = (os.getenv("NODE_ENV") or getattr(settings, "NODE_ENV", "")).strip().lower()

        # If any env indicates production -> block immediately
        disallowed = {"production", "prod", "live"}
        if momo_env in disallowed or sys_env in disallowed or node_env in disallowed:
            return True

        return False

    def validate_amount(self, amount: Decimal) -> bool:
        """Validates that integer VND amount is within MoMo limits [1,000, 50,000,000]."""
        if amount is None:
            return False
        return MIN_MOMO_AMOUNT <= amount <= MAX_MOMO_AMOUNT

    def generate_request_signature(
        self,
        access_key: str,
        amount: int,
        extra_data: str,
        ipn_url: str,
        order_id: str,
        order_info: str,
        partner_code: str,
        redirect_url: str,
        request_id: str,
        request_type: str,
        secret_key: str
    ) -> str:
        """
        Official MoMo Request Signature Canonical String:
        accessKey=$accessKey&amount=$amount&extraData=$extraData&ipnUrl=$ipnUrl&orderId=$orderId&orderInfo=$orderInfo&partnerCode=$partnerCode&redirectUrl=$redirectUrl&requestId=$requestId&requestType=$requestType
        """
        raw_signature = (
            f"accessKey={access_key}&"
            f"amount={amount}&"
            f"extraData={extra_data}&"
            f"ipnUrl={ipn_url}&"
            f"orderId={order_id}&"
            f"orderInfo={order_info}&"
            f"partnerCode={partner_code}&"
            f"redirectUrl={redirect_url}&"
            f"requestId={request_id}&"
            f"requestType={request_type}"
        )
        return hmac.new(
            secret_key.encode("utf-8"),
            raw_signature.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def generate_ipn_signature(
        self,
        access_key: str,
        amount: int,
        extra_data: str,
        message: str,
        order_id: str,
        order_info: str,
        order_type: str,
        partner_code: str,
        pay_type: str,
        request_id: str,
        response_time: int,
        result_code: int,
        trans_id: int,
        secret_key: str,
        include_access_key: bool = True
    ) -> str:
        """
        Official MoMo IPN Verification Signature Canonical String:
        accessKey=$accessKey&amount=$amount&extraData=$extraData&message=$message&orderId=$orderId&orderInfo=$orderInfo&orderType=$orderType&partnerCode=$partnerCode&payType=$payType&requestId=$requestId&responseTime=$responseTime&resultCode=$resultCode&transId=$transId
        """
        if include_access_key and access_key:
            raw_signature = (
                f"accessKey={access_key}&"
                f"amount={amount}&"
                f"extraData={extra_data}&"
                f"message={message}&"
                f"orderId={order_id}&"
                f"orderInfo={order_info}&"
                f"orderType={order_type}&"
                f"partnerCode={partner_code}&"
                f"payType={pay_type}&"
                f"requestId={request_id}&"
                f"responseTime={response_time}&"
                f"resultCode={result_code}&"
                f"transId={trans_id}"
            )
        else:
            raw_signature = (
                f"amount={amount}&"
                f"extraData={extra_data}&"
                f"message={message}&"
                f"orderId={order_id}&"
                f"orderInfo={order_info}&"
                f"orderType={order_type}&"
                f"partnerCode={partner_code}&"
                f"payType={pay_type}&"
                f"requestId={request_id}&"
                f"responseTime={response_time}&"
                f"resultCode={result_code}&"
                f"transId={trans_id}"
            )
        return hmac.new(
            secret_key.encode("utf-8"),
            raw_signature.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def verify_ipn_signature(
        self,
        payload: Dict[str, Any],
        secret_key: Optional[str] = None,
        access_key: Optional[str] = None
    ) -> bool:
        """
        Verifies MoMo IPN callback signature with constant-time comparison.
        Official MoMo Contract:
        - The canonical signature string defined by MoMo starts with `accessKey=$accessKey&...`.
        - However, the server-to-server callback JSON payload sent by MoMo DOES NOT contain the `accessKey` field.
        - Therefore, the access key is ALWAYS obtained from the merchant's server configuration
          (MOMO_ACCESS_KEY), NEVER required to be present in the incoming callback payload body.
        - Validates the presence of truly required payload fields according to MoMo contract:
          partnerCode, orderId, requestId, amount, resultCode.
        """
        secret = secret_key or os.getenv("MOMO_SECRET_KEY") or getattr(settings, "MOMO_SECRET_KEY", "")
        if not secret:
            logger.warning("[MoMoAdapter] Missing MOMO_SECRET_KEY in server configuration.")
            return False

        server_access_key = access_key or os.getenv("MOMO_ACCESS_KEY") or getattr(settings, "MOMO_ACCESS_KEY", "")
        if not server_access_key:
            logger.warning("[MoMoAdapter] Missing MOMO_ACCESS_KEY in server configuration.")
            return False

        incoming_signature = payload.get("signature")
        if not incoming_signature or not isinstance(incoming_signature, str):
            logger.warning("[MoMoAdapter] IPN payload missing or invalid signature field.")
            return False

        # Strictly validate truly required callback fields from MoMo specification
        required_fields = ["partnerCode", "orderId", "requestId", "amount", "resultCode"]
        for field in required_fields:
            if field not in payload or payload[field] is None:
                logger.warning(f"[MoMoAdapter] IPN payload missing required contract field: '{field}'.")
                return False

        try:
            expected_signature = self.generate_ipn_signature(
                access_key=server_access_key,
                amount=int(payload.get("amount", 0)),
                extra_data=str(payload.get("extraData") if payload.get("extraData") is not None else ""),
                message=str(payload.get("message") if payload.get("message") is not None else ""),
                order_id=str(payload.get("orderId", "")),
                order_info=str(payload.get("orderInfo") if payload.get("orderInfo") is not None else ""),
                order_type=str(payload.get("orderType") if payload.get("orderType") is not None else ""),
                partner_code=str(payload.get("partnerCode", "")),
                pay_type=str(payload.get("payType") if payload.get("payType") is not None else ""),
                request_id=str(payload.get("requestId", "")),
                response_time=int(payload.get("responseTime") if payload.get("responseTime") is not None else 0),
                result_code=int(payload.get("resultCode", -1)),
                trans_id=int(payload.get("transId") if payload.get("transId") is not None else 0),
                secret_key=secret,
                include_access_key=True
            )
            return hmac.compare_digest(expected_signature, incoming_signature)
        except Exception as e:
            logger.warning(f"[MoMoAdapter] Error generating expected IPN signature: {e}")
            return False

    def generate_signature(self, payload: Dict[str, Any]) -> str:
        """BasePaymentAdapter compliance helper."""
        if "requestType" in payload:
            return self.generate_request_signature(
                access_key=payload.get("accessKey", ""),
                amount=int(payload.get("amount", 0)),
                extra_data=payload.get("extraData", ""),
                ipn_url=payload.get("ipnUrl", ""),
                order_id=payload.get("orderId", ""),
                order_info=payload.get("orderInfo", ""),
                partner_code=payload.get("partnerCode", ""),
                redirect_url=payload.get("redirectUrl", ""),
                request_id=payload.get("requestId", ""),
                request_type=payload.get("requestType", "payWithMethod"),
                secret_key=payload.get("secretKey") or getattr(settings, "MOMO_SECRET_KEY", "")
            )
        return self.generate_ipn_signature(
            access_key=payload.get("accessKey", ""),
            amount=int(payload.get("amount", 0)),
            extra_data=payload.get("extraData", ""),
            message=payload.get("message", ""),
            order_id=payload.get("orderId", ""),
            order_info=payload.get("orderInfo", ""),
            order_type=payload.get("orderType", ""),
            partner_code=payload.get("partnerCode", ""),
            pay_type=payload.get("payType", ""),
            request_id=payload.get("requestId", ""),
            response_time=int(payload.get("responseTime", 0)),
            result_code=int(payload.get("resultCode", -1)),
            trans_id=int(payload.get("transId", 0)),
            secret_key=payload.get("secretKey") or getattr(settings, "MOMO_SECRET_KEY", "")
        )

    def verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """BasePaymentAdapter compliance helper."""
        payload_copy = dict(payload)
        payload_copy["signature"] = signature
        return self.verify_ipn_signature(payload_copy)

    async def create_payment_request(
        self,
        order_id: str,
        request_id: str,
        amount: int,
        order_info: str,
        extra_data: str = "",
        client: Optional[httpx.AsyncClient] = None,
        timeout_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes HTTP POST /v2/gateway/api/create using payWithMethod flow.
        Official MoMo Onboarding Specification enforces minimum timeout of 30.0 seconds.
        """
        if self.is_production_blocked():
            return {
                "status": "production_blocked",
                "message": "MoMo payment is strictly disabled in production for Phase 7.4B."
            }

        if not self.is_configured():
            return {
                "status": "unconfigured_provider",
                "message": "MoMo provider credentials or callback URLs are not configured."
            }

        # Enforce minimum 30.0s timeout per official MoMo documentation
        configured_timeout = getattr(settings, "MOMO_TIMEOUT_SECONDS", DEFAULT_MOMO_TIMEOUT_SECONDS)
        requested_timeout = float(timeout_seconds) if timeout_seconds is not None else float(configured_timeout)
        effective_timeout = max(requested_timeout, MIN_MOMO_TIMEOUT_SECONDS)

        partner_code = os.getenv("MOMO_PARTNER_CODE") or getattr(settings, "MOMO_PARTNER_CODE")
        access_key = os.getenv("MOMO_ACCESS_KEY") or getattr(settings, "MOMO_ACCESS_KEY")
        secret_key = os.getenv("MOMO_SECRET_KEY") or getattr(settings, "MOMO_SECRET_KEY")
        redirect_url = os.getenv("MOMO_REDIRECT_URL") or getattr(settings, "MOMO_REDIRECT_URL")
        ipn_url = os.getenv("MOMO_IPN_URL") or getattr(settings, "MOMO_IPN_URL")
        endpoint = (os.getenv("MOMO_ENDPOINT") or getattr(settings, "MOMO_ENDPOINT", "https://test-payment.momo.vn")).rstrip("/")
        partner_name = os.getenv("MOMO_PARTNER_NAME") or getattr(settings, "MOMO_PARTNER_NAME", "Badminton AI")
        store_id = os.getenv("MOMO_STORE_ID") or getattr(settings, "MOMO_STORE_ID", "BadmintonCourt01")

        dec_amount = Decimal(str(amount))
        if not self.validate_amount(dec_amount):
            return {
                "status": "invalid_amount",
                "message": f"Số tiền thanh toán MoMo ({amount} VND) không hợp lệ. Cho phép từ 1.000 đến 50.000.000 VND."
            }

        request_type = "payWithMethod"
        signature = self.generate_request_signature(
            access_key=access_key,
            amount=amount,
            extra_data=extra_data,
            ipn_url=ipn_url,
            order_id=order_id,
            order_info=order_info,
            partner_code=partner_code,
            redirect_url=redirect_url,
            request_id=request_id,
            request_type=request_type,
            secret_key=secret_key
        )

        payload = {
            "partnerCode": partner_code,
            "partnerName": partner_name,
            "storeId": store_id,
            "requestId": request_id,
            "amount": int(amount),
            "orderId": order_id,
            "orderInfo": order_info,
            "redirectUrl": redirect_url,
            "ipnUrl": ipn_url,
            "requestType": request_type,
            "extraData": extra_data,
            "lang": "vi",
            "signature": signature
        }

        url = f"{endpoint}/v2/gateway/api/create"
        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=effective_timeout)
            close_client = True

        try:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(f"[MoMoAdapter] HTTP Error {resp.status_code}: {resp.text}")
                return {
                    "status": "provider_error",
                    "message": f"MoMo Gateway trả về mã HTTP {resp.status_code}.",
                    "raw_response": resp.text
                }

            data = resp.json()
            result_code = data.get("resultCode")
            if result_code == 0:
                pay_url = data.get("payUrl")
                if not pay_url:
                    return {
                        "status": "provider_error",
                        "message": "MoMo trả về resultCode=0 nhưng thiếu payUrl."
                    }
                return {
                    "status": "success",
                    "pay_url": pay_url,
                    "deeplink": data.get("deeplink"),
                    "qr_code_url": data.get("qrCodeUrl"),
                    "order_id": data.get("orderId"),
                    "request_id": data.get("requestId"),
                    "raw_data": data
                }
            else:
                return {
                    "status": "provider_rejected",
                    "result_code": result_code,
                    "message": data.get("message", "Giao dịch bị từ chối bởi MoMo."),
                    "raw_data": data
                }

        except httpx.TimeoutException:
            logger.error("[MoMoAdapter] Gateway timeout calling MoMo API create.")
            return {
                "status": "timeout",
                "message": "Kết nối tới cổng thanh toán MoMo bị quá hạn (timeout)."
            }
        except Exception as e:
            logger.error(f"[MoMoAdapter] Network or unexpected exception: {e}")
            return {
                "status": "network_error",
                "message": f"Lỗi kết nối tới MoMo: {str(e)}"
            }
        finally:
            if close_client:
                await client.aclose()
