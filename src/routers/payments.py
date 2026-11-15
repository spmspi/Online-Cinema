from fastapi import APIRouter, HTTPException, Query, Request, status, Depends
import stripe, os
from sqlalchemy import select
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.schemas.movies import MovieListSchema
from src.dependencies.service import get_accounts_email_notificator
from src.notifications.interfaces import EmailSenderInterface
from src.database.models.order import StatusOrderEnum, OrderItemModel
from src.database.models.payments import PaymentsItemModel
from src.settings import Settings, get_settings
from src.database.models.order import OrdersModel
from src.dependencies.payments import pay_order
from src.dependencies.user import get_current_user
from src.database.models.accounts import UserModel
from src.database.models.payments import PaymentsModel, StatusPaymentsEnum
from src.database.engine import get_db

router = APIRouter(tags=["payments"])

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY


@router.get("/checkout/")
async def create_checkout_session(
        order: OrdersModel = Depends(pay_order),
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        ):
    try:
        session = stripe.checkout.Session.create(
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Order ID: {order.id}"},
                    "unit_amount": int(order.total_amount * 100),
                },
                "quantity": 1,
            }],
            metadata={
                "user_id": current_user.id,
                "email": current_user.email,
                "order_id": order.id,
            },
            mode="payment",
            success_url=settings.BASE_URL + "/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.BASE_URL  + "/cancel",
            customer_email=current_user.email,
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/")
async def stripe_webhook(request: Request,
                         email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
                         db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Invalid signature"})
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        session_dict = session.to_dict(for_json=True)
        metadata = session_dict.get("metadata", {})

        user_id = metadata.get("user_id")
        user_email = metadata.get("email")
        order_id = metadata.get("order_id")
        if order_id and user_id:
            stmt = select(OrdersModel).where(OrdersModel.id == int(order_id)).options(selectinload(OrdersModel.order_items))
            result = await db.execute(stmt)
            order = result.scalar_one_or_none()
            if order:
                new_payment = PaymentsModel(
                    user_id=int(user_id),
                    order_id=int(order_id),
                    external_payment_id=session_dict.get("id"),
                    amount=session_dict.get("amount_total") / 100,
                    status=StatusPaymentsEnum.SUCCESSFUL,
                )
                db.add(new_payment)
                await db.flush()
                items_in_order = []
                for item in order.order_items:
                    payment_item = PaymentsItemModel(
                        payment_id=new_payment.id,
                        order_item_id=item.id,
                        price_at_payment=item.price_at_order,
                    )
                    items_in_order.append(item)
                    db.add(payment_item)
                stmt = select(OrdersModel).where(OrdersModel.id == order.id).options(
                    selectinload(OrdersModel.order_items).selectinload(OrderItemModel.movie)
                )
                res = await db.execute(stmt)
                order = res.scalar_one_or_none()
                movie_list = [MovieListSchema.model_validate(item.movie) for item in order.order_items]
                order.status = StatusOrderEnum.PAID
                await db.commit()
                await email_sender.send_payment_successful_email(
                    email=user_email,
                    items=movie_list)
    return {"status": "success"}

@router.get("/success/")
async def stripe_success(
        session_id: str,
        db_session: AsyncSession = Depends(get_db),
):
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {"status": "success",
                "message": "payment successfully completed",
                "stripe_session_id": session_id,
                "user_email": session["customer_email"],
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))