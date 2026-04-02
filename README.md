# Enable Banking API Code Samples

This repository contains code samples for utilizing the [Enable Banking API](https://api.enablebanking.com/).

## Prerequisites   

To successfully use these samples, please follow these steps:

1. Create a developer account at https://enablebanking.com/ by pressing "Get started".

2. Register a new application at https://enablebanking.com/cp/applications.
   If you opt to generate the private key for the application in the browser, the application's
   private key file will be downloaded to your computer. It will be named with the ID assigned to
   the application and have a ".pem" extension (e.g., `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.pem`).

4. Modify values of the `keyPath` and `applicationId` fields in the `config.json` file with the
   values obtained in previous step.
   *This step in not necessary if you are going to use our Postman collection.* 

5. Navigate to a folder with code samples in a language of your choice and follow the instructions
   provided in the README.md file, which can be found there.

## Quick Start: OTP Bank Hungary CLI Tool

If you want to authenticate with **OTP Bank Hungary** using an interactive CLI tool, we provide a ready-to-use script:

```bash
python3 otp_hungary_cli_auth.py
```

This interactive script will:
- ✅ Guide you through the setup process step-by-step
- ✅ Explain how to obtain all required credentials
- ✅ Handle the complete authentication flow with OTP Bank Hungary
- ✅ Display your account balances and recent transactions

**See [OTP_HUNGARY_README.md](OTP_HUNGARY_README.md) for detailed instructions.**

For further information please refer to the [Enable Banking Docs](https://enablebanking.com/docs/)
