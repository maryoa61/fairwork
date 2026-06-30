"""
Example end-to-end test outline for FairWork, following the pattern shown
in the GenLayer documentation (tooling-setup page). Run this against a
local GenLayer Studio instance.

This is a starting skeleton — fill in the actual GenLayer test SDK calls
for your installed SDK version (deploy_intelligent_contract,
call_contract_method, send_transaction, create_new_account, etc.)
"""

import pytest

CONTRACT_PATH = "contracts/fairwork.py"


def test_happy_path_approval():
    """
    Client creates a job with one milestone, freelancer submits,
    client approves -> freelancer should receive the full milestone amount,
    no AI call should be required.
    """
    # account_client = create_new_account()
    # account_freelancer = create_new_account()
    # contract_code = open(CONTRACT_PATH).read()
    # address, _ = deploy_intelligent_contract(account_client, contract_code, "{}")
    # job_id = send_transaction(account_client, address, "create_job", [...])
    # send_transaction(account_freelancer, address, "submit_milestone", [...])
    # send_transaction(account_client, address, "approve_milestone", [...])
    # job = call_contract_method(address, account_client, "get_job", [job_id])
    # assert job["milestones"][0]["status"] == "approved"
    pass


def test_dispute_path_triggers_arbitration():
    """
    Client disputes a submitted milestone, freelancer replies, and the
    contract should resolve the dispute via gl.eq_principle_prompt_comparative,
    ending with status == "resolved" and a payout_to_freelancer between
    0 and the milestone amount.
    """
    pass


def test_milestone_amounts_must_match_value_sent():
    """
    create_job should reject a job where the sum of milestone amounts
    does not equal the value attached to the transaction.
    """
    pass
