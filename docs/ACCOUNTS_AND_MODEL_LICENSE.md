# Accounts and model use

Authentication is enabled by default and in this workspace's local configuration. Open the app and create an account with an email address and a password of at least 12 characters. Log out from More. There is no public admin page. Registered accounts can investigate, create cases and explore their own entities; ownership checks apply independently of role. The protected operator API remains unavailable to normal accounts.

Passwords are salted and hashed with scrypt. Plaintext passwords are not stored. Random session tokens are placed in HttpOnly, SameSite=Strict cookies; only token hashes are stored in the database. Sessions expire after 12 hours. Logout revokes all sessions and extension tokens for that account and clears the browser query cache. API session failures return the browser to the login gate. Account-service failures are shown as service errors, not incorrect-password errors.

Local account records persist in `storage/threatgraph.db`. Existing local investigations remain preserved under their original ownership and are not automatically assigned to a new signup. Do not expose or copy this database publicly. No email verification, self-service password reset, or account deletion UI is implemented. Use HTTPS and `SECURE_COOKIES=true` when hosting; retain authentication, configure trusted origins and a durable database, and replace the development in-memory rate limiter with deployment-level limits.

## Image-model license

Active artifact: `s-gehring/detectra-openfake`, pinned revision `c84565e5bf8969d95908e12844f551e77ae87105`. Its model card and the publisher's current card were reviewed on 2026-11-07. The weights are CC BY-NC 4.0: noncommercial use only.

An educational, noncommercial college demonstration is generally consistent with this restriction. Do not assume that a free public service is noncommercial: commercial advantage also matters. Paid APIs, subscriptions, client services and business use need appropriate permission or a replacement with suitable terms. Fine-tuning does not automatically remove the original restrictions.

When sharing, retain attribution, link to the license, indicate changes, and do not imply endorsement. No additional legal or technical restrictions may prevent uses permitted by the license. The upstream card also identifies Qwen research-license material and other data terms; this notice is not commercial clearance for all upstream material.

Attribution: model integration by ThreatGraph uses Detectra OpenFake by s-gehring; Detectra v3 by TensorFold; Community Forensics by Jeongsoo Park and Andrew Owens; OpenFake by Victor Livernoche, Akshatha Arodi, Andreea Musulan, Zachary Yang, Adam Salvail, Gaétan Marceau Caron, Jean-François Godbout and Reihaneh Rabbany. Improved using Qwen, as disclosed by the publisher. ThreatGraph has not modified the installed checkpoint; it adds local inference integration and evaluation.

Sources:
- https://huggingface.co/s-gehring/detectra-openfake
- https://creativecommons.org/licenses/by-nc/4.0/
- Pinned upstream model card: `models/image/detectra-openfake/README.md`

The model provides a fallible screening signal, not proof of origin or fraud. Do not use its output as the sole basis for consequential decisions about people or their work.
