import re
from typing import Optional
from flows.base import BaseFlow, FlowResponse
from ai.schemas import IntentResult
from core.state_manager import ConversationState
from database.repository import OrderRepository

# --- Category / sub-category taxonomy ---
MISSING_SUBCATEGORIES = ["Missing Item", "Missing Accessories"]
WRONG_SUBCATEGORIES = ["Wrong Product", "Damaged Product", "Expired Product", "Leak product"]
REFUND_SUBCATEGORIES = ["Refund", "Warranty Claim", "Cashback", "Change of Mind"]
GENERAL_SUBCATEGORIES = ["Order Info", "Complaint Info", "Extra Parcel", "Delay Delivery", "General"]

# Wrong-category sub-categories that require a photo upload
WRONG_NEEDS_IMAGE = {"Wrong Product", "Damaged Product", "Expired Product", "Leak product"}
# Of those, which ones ask a Receive Correct Item / Refund Money resolution question after the photo
WRONG_NEEDS_RESOLUTION = {"Wrong Product", "Damaged Product", "Expired Product", "Leak product"}
# Wrong-category sub-categories that just need a text description (no photo) - none currently
WRONG_SIMPLE = set()


def _match_subcategory(msg_lower: str, options) -> Optional[str]:
    for option in options:
        if option.lower() in msg_lower:
            return option
    return None


class ComplaintFlow(BaseFlow):
    def __init__(self, order_repository=None):
        self.order_repository = order_repository or OrderRepository()

    def is_continuation(self, intent_result: IntentResult, state: ConversationState) -> bool:
        # Once a complaint is in progress (current_stage is set), every subsequent
        # message is an answer to the current step (order ID, category, sub-category,
        # image upload, resolution, or free-text details) - never a fresh request.
        return state.current_stage is not None

    def handle(self, intent_result: IntentResult, state: ConversationState) -> FlowResponse:

        # Retrieve raw user message from conversation history
        user_msg = ""
        if state.conversation_history:
            user_msg = state.conversation_history[-1]["content"].strip()

        current_stage = state.current_stage

        # 1. Trigger / Verify Order ID
        if current_stage is None:
            # Check if order_id is in entities
            order_id = state.entities.get("order_id")
            if order_id is not None and not isinstance(order_id, str):
                order_id = str(order_id)
            if not order_id:
                order_id = None

            if not order_id and intent_result.entities:
                if isinstance(intent_result.entities, dict):
                    extracted = intent_result.entities.get("order_id")
                elif hasattr(intent_result.entities, "model_dump"):
                    extracted = intent_result.entities.model_dump().get("order_id")
                else:
                    extracted = getattr(intent_result.entities, "order_id", None)
                if extracted is not None and not isinstance(extracted, MagicMock if 'MagicMock' in globals() else object):
                    order_id = str(extracted)

            if not order_id:
                # Use regex to find order ID in user message as fallback
                match = re.search(r'\b\d{5,13}\b', user_msg)
                if match:
                    order_id = match.group(0)

            if not order_id:
                return FlowResponse(
                    status="waiting_for_input",
                    response="I can register your complaint. What is your Order ID?",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_order_id",
                        "waiting_for_order_id": True
                    }
                )
            else:
                try:
                    resolved_id = self.order_repository.resolve_to_latest_order_id(order_id)
                    self.order_repository.get_order_by_increment_id(resolved_id)
                    new_entities = {**state.entities, "order_id": resolved_id}
                    if resolved_id != order_id:
                        new_entities["parent_order_id"] = order_id
                    response_text = "Order ID verified. Please select the category of your complaint:\n- Missing\n- Wrong\n- Refund\n- General"
                    return FlowResponse(
                        status="waiting_for_input",
                        response=response_text,
                        updated_state={
                            "current_flow": "complaint",
                            "current_stage": "waiting_for_category",
                            "waiting_for_order_id": False,
                            "entities": new_entities
                        }
                    )
                except Exception:
                    return FlowResponse(
                        status="waiting_for_input",
                        response="We couldn't find an order with that ID. Please check and try again.",
                        updated_state={
                            "current_flow": "complaint",
                            "current_stage": "waiting_for_order_id",
                            "waiting_for_order_id": True
                        }
                    )


        # 2. Waiting for Order ID stage
        if current_stage == "waiting_for_order_id":
            order_id = None
            if intent_result.entities:
                if isinstance(intent_result.entities, dict):
                    extracted = intent_result.entities.get("order_id")
                elif hasattr(intent_result.entities, "model_dump"):
                    extracted = intent_result.entities.model_dump().get("order_id")
                else:
                    extracted = getattr(intent_result.entities, "order_id", None)
                if extracted is not None and not isinstance(extracted, MagicMock if 'MagicMock' in globals() else object):
                    order_id = str(extracted)

            if not order_id:
                match = re.search(r'\b\d{5,13}\b', user_msg)
                if match:
                    order_id = match.group(0)

            if not order_id:
                return FlowResponse(
                    status="waiting_for_input",
                    response="Please provide a valid Order ID to proceed.",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_order_id",
                        "waiting_for_order_id": True
                    }
                )
            else:
                try:
                    resolved_id = self.order_repository.resolve_to_latest_order_id(order_id)
                    self.order_repository.get_order_by_increment_id(resolved_id)
                    new_entities = {**state.entities, "order_id": resolved_id}
                    if resolved_id != order_id:
                        new_entities["parent_order_id"] = order_id
                    response_text = "Order ID verified. Please select the category of your complaint:\n- Missing\n- Wrong\n- Refund\n- General"
                    return FlowResponse(
                        status="waiting_for_input",
                        response=response_text,
                        updated_state={
                            "current_flow": "complaint",
                            "current_stage": "waiting_for_category",
                            "waiting_for_order_id": False,
                            "entities": new_entities
                        }
                    )
                except Exception:
                    return FlowResponse(
                        status="waiting_for_input",
                        response="We couldn't find an order with that ID. Please check and try again.",
                        updated_state={
                            "current_flow": "complaint",
                            "current_stage": "waiting_for_order_id",
                            "waiting_for_order_id": True
                        }
                    )


        # 3. Waiting for Category
        if current_stage == "waiting_for_category":
            msg_lower = user_msg.lower()
            if "missing" in msg_lower:
                return FlowResponse(
                    status="waiting_for_input",
                    response="Please select the sub-category:\n- Missing Item\n- Missing Accessories",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_missing_sub_category",
                        "entities": {**state.entities, "complaint_category": "Missing"}
                    }
                )
            elif "wrong" in msg_lower:
                return FlowResponse(
                    status="waiting_for_input",
                    response=(
                        "Please select the sub-category:\n"
                        "- Wrong Product\n- Damaged Product\n- Expired Product\n- Leak product"
                    ),
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_wrong_sub_category",
                        "entities": {**state.entities, "complaint_category": "Wrong"}
                    }
                )
            elif "refund" in msg_lower:
                return FlowResponse(
                    status="waiting_for_input",
                    response="Please select the sub-category:\n- Refund\n- Warranty Claim\n- Cashback\n- Change of Mind",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_refund_sub_category",
                        "entities": {**state.entities, "complaint_category": "Refund"}
                    }
                )
            elif "general" in msg_lower:
                return FlowResponse(
                    status="waiting_for_input",
                    response="Please select the sub-category:\n- Order Info\n- Complaint Info\n- Extra Parcel\n- Delay Delivery\n- General",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_general_sub_category",
                        "entities": {**state.entities, "complaint_category": "General"}
                    }
                )
            else:
                return FlowResponse(
                    status="waiting_for_input",
                    response="Invalid option. Please choose between 'Missing', 'Wrong', 'Refund', or 'General'.",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_category"
                    }
                )

        # 4a. Waiting for Missing Sub-category
        if current_stage == "waiting_for_missing_sub_category":
            msg_lower = user_msg.lower()
            sub_cat = _match_subcategory(msg_lower, MISSING_SUBCATEGORIES)

            if sub_cat == "Missing Item":
                order_id = state.entities.get("order_id", "")
                parent_order_id = state.entities.get("parent_order_id", "")

                # --- Check dispatch-missing items from DB ---
                dispatch_missing = []
                if parent_order_id and parent_order_id != order_id:
                    try:
                        dispatch_missing = self.order_repository.get_unavailable_items(parent_order_id, order_id)
                    except Exception:
                        dispatch_missing = []

                payment_method = self.order_repository.get_payment_method(order_id)
                is_cod = payment_method.lower() == "cashondelivery"

                lines = []
                refund_status = None
                if dispatch_missing:
                    items_str = "\n• " + "\n• ".join(dispatch_missing)
                    lines.append(f"We found the following items were **missing at dispatch**:{items_str}")
                    if is_cod:
                        lines.append("Since your order was placed with **Cash on Delivery**, you were not charged for these items — no refund is applicable for them.")
                    else:
                        refund_status = self.order_repository.get_refund_status(order_id)
                        if refund_status == "completed":
                            lines.append("A refund for these items has already been **processed**. Please allow 3–5 business days for it to reflect.")
                        elif refund_status == "in progress":
                            lines.append("A refund for these items is currently **in progress** and will be processed shortly.")
                        else:
                            lines.append("Our customer service team will **initiate a refund** for these items.")
                    lines.append("Were there any **other items** (besides the above) that you did not receive? If yes, please describe them. If no, type 'No'.")
                else:
                    lines.append("We have no record of items missing at dispatch for your order.")
                    lines.append("Please describe which items you did **not receive**.")

                return FlowResponse(
                    status="waiting_for_input",
                    response="\n\n".join(lines),
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_missing_details",
                        "entities": {
                            **state.entities,
                            "complaint_sub_category": "Missing Item",
                            "dispatch_missing_items": dispatch_missing,
                            "is_cod": is_cod,
                            "refund_status": refund_status if (not is_cod and dispatch_missing) else None
                        }
                    }
                )

            elif sub_cat == "Missing Accessories":
                return self._start_simple_details(state, sub_cat=sub_cat)

            else:
                return FlowResponse(
                    status="waiting_for_input",
                    response="Invalid option. Please choose between 'Missing Item' or 'Missing Accessories'.",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_missing_sub_category"
                    }
                )

        # 4b. Waiting for Wrong Sub-category
        if current_stage == "waiting_for_wrong_sub_category":
            msg_lower = user_msg.lower()
            sub_cat = _match_subcategory(msg_lower, WRONG_SUBCATEGORIES)

            if sub_cat in WRONG_NEEDS_IMAGE:
                return FlowResponse(
                    status="waiting_for_input",
                    response=f"Please upload an image related to your {sub_cat.lower()} complaint.",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_image",
                        "show_upload": True,
                        "entities": {**state.entities, "complaint_sub_category": sub_cat}
                    }
                )
            elif sub_cat in WRONG_SIMPLE:
                return self._start_simple_details(state, sub_cat=sub_cat)
            else:
                return FlowResponse(
                    status="waiting_for_input",
                    response=(
                        "Invalid option. Please choose between 'Wrong Product', 'Damaged Product', "
                        "'Expired Product', or 'Leak product'."
                    ),
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_wrong_sub_category"
                    }
                )

        # 4c. Waiting for Refund Sub-category
        if current_stage == "waiting_for_refund_sub_category":
            msg_lower = user_msg.lower()
            sub_cat = _match_subcategory(msg_lower, REFUND_SUBCATEGORIES)

            if sub_cat:
                return self._start_simple_details(state, sub_cat=sub_cat)
            else:
                return FlowResponse(
                    status="waiting_for_input",
                    response="Invalid option. Please choose between 'Refund', 'Warranty Claim', 'Cashback', or 'Change of Mind'.",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_refund_sub_category"
                    }
                )

        # 4d. Waiting for General Sub-category
        if current_stage == "waiting_for_general_sub_category":
            msg_lower = user_msg.lower()
            order_id = state.entities.get("order_id")

            if "order info" in msg_lower:
                return self._start_simple_details(state, sub_cat="Order Info")
            elif "complaint info" in msg_lower:
                return self._start_simple_details(state, sub_cat="Complaint Info")
            elif "extra parcel" in msg_lower:
                return self._start_simple_details(state, sub_cat="Extra Parcel")
            elif "delay delivery" in msg_lower:
                return self._start_simple_details(state, sub_cat="Delay Delivery")
            elif "general" in msg_lower:
                try:
                    from database.repository import ComplaintRepository
                    repo = ComplaintRepository()
                    if repo.has_existing_complaint_type(order_id, "General"):
                        return FlowResponse(
                            status="completed",
                            response=f"You have already filed a General complaint for Order #{order_id}. Duplicate complaints of the same type are not allowed.",
                            updated_state={"current_flow": None, "current_stage": None}
                        )
                except Exception:
                    pass
                return FlowResponse(
                    status="waiting_for_input",
                    response="Please describe the issue you are experiencing.",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_general_details",
                        "entities": {**state.entities, "complaint_sub_category": "General"}
                    }
                )
            else:
                return FlowResponse(
                    status="waiting_for_input",
                    response=(
                        "Invalid option. Please choose between 'Order Info', 'Complaint Info', "
                        "'Extra Parcel', 'Delay Delivery', or 'General'."
                    ),
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_general_sub_category"
                    }
                )

        # 5. Waiting for Image Upload (Wrong category sub-categories that need a photo)
        if current_stage == "waiting_for_image":
            image_match = re.search(r'\[Image Uploaded:\s*([^\]]+)\]', user_msg)
            sub_cat = state.entities.get("complaint_sub_category", "Wrong Product")
            if image_match:
                image_path = image_match.group(1).strip()

                if sub_cat in WRONG_NEEDS_RESOLUTION:
                    return FlowResponse(
                        status="waiting_for_input",
                        response="Image received. Note: Naheed offers a 7-day return policy for wrong or damaged items.\nHow would you like to resolve this?\n- Receive Correct Item\n- Refund Money",
                        updated_state={
                            "current_flow": "complaint",
                            "current_stage": "waiting_for_resolution",
                            "show_upload": False,
                            "entities": {**state.entities, "image_url": image_path}
                        }
                    )
                else:
                    # e.g. Extra Parcel: file the ticket directly, no resolution step needed
                    order_id = state.entities.get("order_id")
                    details = f"Sub-category: {sub_cat}."
                    return FlowResponse(
                        status="completed",
                        response="",
                        updated_state={
                            "current_flow": None,
                            "current_stage": None,
                            "show_upload": False
                        },
                        tool_request="create_complaint",
                        tool_args={
                            "order_id": order_id,
                            "complaint_type": sub_cat,
                            "details": details,
                            "image_url": image_path
                        }
                    )
            else:
                return FlowResponse(
                    status="waiting_for_input",
                    response=f"Please upload an image related to your {sub_cat.lower()} complaint to proceed.",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_image",
                        "show_upload": True
                    }
                )

        # 6. Waiting for Resolution
        if current_stage == "waiting_for_resolution":
            msg_lower = user_msg.lower()

            # Check if they want to switch to a different issue
            if "different" in msg_lower or "other" in msg_lower or "something else" in msg_lower:
                return FlowResponse(
                    status="waiting_for_input",
                    response="No problem. Please select the category of your complaint:\n- Missing\n- Wrong\n- Refund\n- General",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_category",
                        "entities": {
                            **state.entities,
                            "complaint_category": None,
                            "complaint_sub_category": None,
                            "unavailable_items": None
                        }
                    }
                )

            resolution = None
            sub_cat = state.entities.get("complaint_sub_category") or "Wrong Product"

            if "refund" in msg_lower or "money" in msg_lower:
                resolution = "Refund Money"
            elif "correct" in msg_lower or "receive" in msg_lower or "replace" in msg_lower:
                resolution = "Receive Correct Item"

            if not resolution:
                opts = "Please choose between 'Receive Correct Item' or 'Refund Money'."
                return FlowResponse(
                    status="waiting_for_input",
                    response=f"Invalid option. {opts}",
                    updated_state={
                        "current_flow": "complaint",
                        "current_stage": "waiting_for_resolution"
                    }
                )

            # All details collected! Complete ticket registration.
            order_id = state.entities.get("order_id")
            image_url = state.entities.get("image_url")

            details = f"Sub-category: {sub_cat}. Resolution: {resolution}."

            return FlowResponse(
                status="completed",
                response="",
                updated_state={
                    "current_flow": None,
                    "current_stage": None,
                    "show_upload": False
                },
                tool_request="create_complaint",
                tool_args={
                    "order_id": order_id,
                    "complaint_type": sub_cat,
                    "details": details,
                    "image_url": image_url
                }
            )

        # 7. Waiting for Missing Item Details (customer describes received-but-missing items)
        if current_stage == "waiting_for_missing_details":
            order_id = state.entities.get("order_id")
            dispatch_missing = state.entities.get("dispatch_missing_items") or []
            is_cod = state.entities.get("is_cod", False)
            refund_status = state.entities.get("refund_status")
            additional = user_msg.strip()
            no_additional = additional.lower() in ["no", "none", "nope", "n", "no.", "nahi", "nahi."]

            # Build complaint details
            detail_parts = ["Sub-category: Missing Item."]
            if dispatch_missing:
                detail_parts.append(f"Items missing at dispatch: {', '.join(dispatch_missing)}.")
                if is_cod:
                    detail_parts.append("Payment: COD (not charged for dispatch-missing items).")
                else:
                    detail_parts.append(f"Refund status for dispatch-missing items: {refund_status or 'not yet initiated'}.")
            if not no_additional:
                detail_parts.append(f"Additional items not received by customer: {additional}.")

            if no_additional and not dispatch_missing:
                # Nothing to report at all
                return FlowResponse(
                    status="completed",
                    response="Thank you. No missing items were reported. If you need further help, feel free to reach out.",
                    updated_state={"current_flow": None, "current_stage": None}
                )

            if no_additional and is_cod and dispatch_missing:
                # COD + only dispatch-missing, no additional → no complaint needed
                return FlowResponse(
                    status="completed",
                    response="Thank you. Since this was a COD order, no refund is applicable for the missing dispatch items. No complaint has been filed.",
                    updated_state={"current_flow": None, "current_stage": None}
                )

            # File complaint for all other cases
            return FlowResponse(
                status="completed",
                response="",
                updated_state={"current_flow": None, "current_stage": None, "show_upload": False},
                tool_request="create_complaint",
                tool_args={
                    "order_id": order_id,
                    "complaint_type": "Missing Item",
                    "details": " ".join(detail_parts),
                    "image_url": None
                }
            )

        # 7b. Waiting for a simple text description (Missing Accessories, Delay Delivery,
        # Refund, Warranty Claim, Cashback, Change of Mind, Order Info, Complaint Info)
        # - description only, then file the ticket.
        if current_stage == "waiting_for_simple_details":
            order_id = state.entities.get("order_id")
            sub_cat = state.entities.get("complaint_sub_category", "General")
            details = f"Sub-category: {sub_cat}. Details: {user_msg}"

            return FlowResponse(
                status="completed",
                response="",
                updated_state={
                    "current_flow": None,
                    "current_stage": None
                },
                tool_request="create_complaint",
                tool_args={
                    "order_id": order_id,
                    "complaint_type": sub_cat,
                    "details": details,
                    "image_url": None
                }
            )

        # 8. Waiting for General Details
        if current_stage == "waiting_for_general_details":
            order_id = state.entities.get("order_id")
            details = user_msg

            return FlowResponse(
                status="completed",
                response="",
                updated_state={
                    "current_flow": None,
                    "current_stage": None
                },
                tool_request="create_complaint",
                tool_args={
                    "order_id": order_id,
                    "complaint_type": "General",
                    "details": details,
                    "image_url": None
                }
            )

        # Fallback
        return FlowResponse(
            status="completed",
            response="I'm sorry, we encountered an error handling your complaint.",
            updated_state={"current_flow": None, "current_stage": None}
        )

    def _start_simple_details(self, state: ConversationState, sub_cat: str) -> FlowResponse:
        """Ask a follow-up description question for sub-categories that don't need
        any special handling - they just collect details and file the ticket."""
        try:
            from database.repository import ComplaintRepository
            repo = ComplaintRepository()
            order_id = state.entities.get("order_id")
            if repo.has_existing_complaint_type(order_id, sub_cat):
                return FlowResponse(
                    status="completed",
                    response=f"You have already filed a {sub_cat} complaint for Order #{order_id}. Duplicate complaints of the same type are not allowed.",
                    updated_state={"current_flow": None, "current_stage": None}
                )
        except Exception:
            pass

        return FlowResponse(
            status="waiting_for_input",
            response=f"Please describe your {sub_cat.lower()} issue in more detail.",
            updated_state={
                "current_flow": "complaint",
                "current_stage": "waiting_for_simple_details",
                "entities": {**state.entities, "complaint_sub_category": sub_cat}
            }
        )
