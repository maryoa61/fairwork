# Manual deployment notes (GenLayer Studio)

1. Open https://studio.genlayer.com/contracts
2. Click "New Contract" (or similar) and paste the contents of
   `contracts/fairwork.py`.
3. Deploy — no constructor arguments are required.
4. Try the flow:
   - Switch to "client" account, call `create_job` with:
     - freelancer = another test account address
     - description = e.g. "Build a 5-page marketing website"
     - milestone_descriptions = ["Wireframes approved", "Final site deployed"]
     - milestone_amounts = [20, 80]
     - value sent = 100
   - Switch to "freelancer" account, call `submit_milestone(job_id, 0, note, url)`
   - Switch back to "client":
     - Approve happy path: `approve_milestone(job_id, 0)`
     - Or dispute path: `raise_dispute(job_id, 0, "reason")`
   - If disputed, switch to "freelancer": `reply_to_dispute(job_id, 0, "defense")`
     — this triggers the AI arbitration; watch Node Logs for each
       validator's independent verdict and the consensus check.
5. Call `get_job(job_id)` / `get_milestone(job_id, index)` to inspect state.

For testnet (Bradbury) deployment, follow the CLI/JS deployment guide in
the GenLayer docs once you've validated the flow in Studio.
