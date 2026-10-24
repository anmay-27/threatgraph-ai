# Local browser extension preview

Load this directory as an unpacked Manifest V3 extension in Chrome/Edge developer mode. Start the local API on 127.0.0.1:8000 and frontend on localhost:3000. Click the extension, review the URL, then click Analyze. Right-click actions only select a URL; submission still requires the Analyze button.

No automatic scanning, browsing-history permission, content scripts, file uploads or page-cookie collection. In account mode, sign in to the web app, create a short-lived extension token, and paste it into the popup. The token stays in the popup only and expires after 12 hours; signing out revokes current tokens. Image submission is not implemented. Local-mode URL submission and a real completed result were verified in an isolated Edge profile; account-mode token use remains unverified.
