# { "Depends": "py-genlayer:test" }
"""
FairWork — Milestone-based Freelance Escrow with AI Dispute Resolution
========================================================================

A GenLayer Intelligent Contract that lets a Client and a Freelancer agree on
a job broken into milestones, lock funds in escrow, and release payment
either by mutual agreement OR — when they disagree — through a decentralized
AI arbitration process powered by GenLayer's Optimistic Democracy consensus.

Why this needs GenLayer (and not a normal smart contract):
  - The arbitration step judges natural-language evidence against the
    original milestone description. That is a subjective, non-deterministic
    task that only makes sense if multiple independent validators (each
    potentially running a different LLM) can reach a verifiable consensus
    on the outcome. This is done with `gl.eq_principle_prompt_comparative`.
  - If the freelancer points to a URL as proof of delivery, the contract
    fetches that page live, from inside consensus, with `gl.get_webpage`
    — no external oracle needed.

State design
------------
jobs            : dict[int, Job]            -- all jobs ever created
next_job_id     : int                        -- auto-incrementing id

Job fields:
  client, freelancer  : str (addresses, as text for simplicity in Studio)
  description         : str  -- overall job description (the "contract")
  milestones          : list[Milestone]
  total_locked        : int  -- total GEN/credits locked in escrow
  released            : int  -- amount already released to freelancer
  closed              : bool

Milestone fields:
  description     : str   -- what "done" means for this milestone
  amount          : int   -- portion of total_locked assigned to it
  status          : str   -- "pending" | "submitted" | "approved" |
                             "disputed" | "resolved"
  submission_note : str   -- freelancer's delivery note
  submission_url  : str   -- optional proof-of-work URL
  client_objection: str   -- client's reason for disputing
  freelancer_reply: str   -- freelancer's defense
  resolution_note : str   -- AI arbitration reasoning (stored for transparency)
  payout_to_freelancer : int  -- final amount the AI decided to release
"""

from genlayer import *
import json
import typing


@gl.contract
class FairWork(gl.Contract):
    jobs: TreeMap[u256, "Job"]
    next_job_id: u256

    def __init__(self):
        self.next_job_id = u256(1)

    # ------------------------------------------------------------------
    # Job creation
    # ------------------------------------------------------------------

    @gl.public.write.payable
    def create_job(
        self,
        freelancer: Address,
        description: str,
        milestone_descriptions: list[str],
        milestone_amounts: list[int],
    ) -> u256:
        """
        Client deploys funds (msg.value) and defines the job + milestones.
        The sum of milestone_amounts must equal the value sent.
        """
        assert len(milestone_descriptions) == len(milestone_amounts), (
            "milestone descriptions and amounts must match in length"
        )
        assert len(milestone_descriptions) > 0, "at least one milestone is required"

        total = sum(milestone_amounts)
        assert total == gl.message.value, (
            "sum of milestone amounts must equal the value sent"
        )

        job_id = self.next_job_id
        self.next_job_id = u256(int(self.next_job_id) + 1)

        milestones: list[Milestone] = []
        for desc, amount in zip(milestone_descriptions, milestone_amounts):
            milestones.append(
                Milestone(
                    description=desc,
                    amount=amount,
                    status="pending",
                    submission_note="",
                    submission_url="",
                    client_objection="",
                    freelancer_reply="",
                    resolution_note="",
                    payout_to_freelancer=0,
                )
            )

        self.jobs[job_id] = Job(
            client=gl.message.sender_address,
            freelancer=freelancer,
            description=description,
            milestones=milestones,
            total_locked=total,
            released=0,
            closed=False,
        )
        return job_id

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    @gl.public.write
    def submit_milestone(
        self, job_id: u256, milestone_index: int, note: str, proof_url: str
    ) -> None:
        job = self.jobs[job_id]
        assert gl.message.sender_address == job.freelancer, "only the freelancer can submit work"
        m = job.milestones[milestone_index]
        assert m.status == "pending", "milestone is not in a submittable state"

        m.submission_note = note
        m.submission_url = proof_url
        m.status = "submitted"

    # ------------------------------------------------------------------
    # Happy path: client approves, no AI needed
    # ------------------------------------------------------------------

    @gl.public.write
    def approve_milestone(self, job_id: u256, milestone_index: int) -> None:
        job = self.jobs[job_id]
        assert gl.message.sender_address == job.client, "only the client can approve"
        m = job.milestones[milestone_index]
        assert m.status == "submitted", "milestone must be submitted first"

        m.status = "approved"
        m.payout_to_freelancer = m.amount
        job.released += m.amount
        gl.emit_transfer(job.freelancer, m.amount)
        self._maybe_close(job)

    # ------------------------------------------------------------------
    # Unhappy path: client objects -> freelancer can reply -> AI resolves
    # ------------------------------------------------------------------

    @gl.public.write
    def raise_dispute(self, job_id: u256, milestone_index: int, reason: str) -> None:
        job = self.jobs[job_id]
        assert gl.message.sender_address == job.client, "only the client can dispute"
        m = job.milestones[milestone_index]
        assert m.status == "submitted", "can only dispute a submitted milestone"

        m.client_objection = reason
        m.status = "disputed"

    @gl.public.write
    def reply_to_dispute(self, job_id: u256, milestone_index: int, reply: str) -> None:
        job = self.jobs[job_id]
        assert gl.message.sender_address == job.freelancer, "only the freelancer can reply"
        m = job.milestones[milestone_index]
        assert m.status == "disputed", "milestone is not under dispute"

        m.freelancer_reply = reply
        self._resolve_dispute(job, m)

    # ------------------------------------------------------------------
    # AI arbitration — the part that actually needs GenLayer's consensus
    # ------------------------------------------------------------------

    def _resolve_dispute(self, job: "Job", m: "Milestone") -> None:
        evidence_page = ""
        if m.submission_url:
            def fetch_proof() -> str:
                try:
                    return gl.get_webpage(m.submission_url, mode="text")[:4000]
                except Exception:
                    return "(could not fetch proof URL)"
            evidence_page = gl.eq_principle_strict_eq(fetch_proof)

        principle = (
            "Two independent assessments of a freelance dispute should be "
            "considered equivalent if they agree on (a) whether the work "
            "substantially satisfies the milestone description, and "
            "(b) the payout percentage to within 10 percentage points."
        )

        def judge() -> str:
            prompt = f"""
You are an impartial freelance-work arbitrator. Decide how much of the
milestone payment the freelancer should receive, based only on the
evidence below. Be fair to both sides.

ORIGINAL JOB DESCRIPTION:
{job.description}

MILESTONE DEFINITION (what counts as "done"):
{m.description}
Milestone amount: {m.amount}

FREELANCER'S SUBMISSION NOTE:
{m.submission_note}

FREELANCER'S PROOF-OF-WORK PAGE CONTENT (may be empty):
{evidence_page}

CLIENT'S OBJECTION:
{m.client_objection}

FREELANCER'S REPLY TO OBJECTION:
{m.freelancer_reply}

Respond using ONLY this JSON format, nothing else:
{{
  "reasoning": str,
  "payout_percent": int
}}
"payout_percent" must be an integer from 0 to 100, representing the
percentage of the milestone amount that should go to the freelancer.
"""
            res = gl.exec_prompt(prompt)
            res = res.replace("```json", "").replace("```", "").strip()
            data = json.loads(res)
            pct = max(0, min(100, int(data["payout_percent"])))
            return json.dumps({"reasoning": data["reasoning"], "payout_percent": pct})

        verdict_raw = gl.eq_principle_prompt_comparative(judge, principle)
        verdict = json.loads(verdict_raw)

        payout = (m.amount * verdict["payout_percent"]) // 100
        m.payout_to_freelancer = payout
        m.resolution_note = verdict["reasoning"]
        m.status = "resolved"

        job.released += payout
        if payout > 0:
            gl.emit_transfer(job.freelancer, payout)
        refund = m.amount - payout
        if refund > 0:
            gl.emit_transfer(job.client, refund)

        self._maybe_close(job)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _maybe_close(self, job: "Job") -> None:
        if all(m.status in ("approved", "resolved") for m in job.milestones):
            job.closed = True

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    @gl.public.view
    def get_job(self, job_id: u256) -> "Job":
        return self.jobs[job_id]

    @gl.public.view
    def get_milestone(self, job_id: u256, milestone_index: int) -> "Milestone":
        return self.jobs[job_id].milestones[milestone_index]

    @gl.public.view
    def get_job_count(self) -> u256:
        return self.next_job_id


@allow_storage
class Milestone:
    description: str
    amount: int
    status: str
    submission_note: str
    submission_url: str
    client_objection: str
    freelancer_reply: str
    resolution_note: str
    payout_to_freelancer: int


@allow_storage
class Job:
    client: Address
    freelancer: Address
    description: str
    milestones: list[Milestone]
    total_locked: int
    released: int
    closed: bool
