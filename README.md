# RFC: Secure File Transfer Protocols (CMPE 272 Final Project)

**Status:** Final  
**Author:** Robbie Tambunting  
**Date:** May 14, 2026  

## Abstract

This document specifies two distinct architectural approaches for securely transferring a large file (e.g., 4 GB) over an untrusted network while maintaining Confidentiality, Integrity, Authentication, and Availability (CIAA). Approach A utilizes transport-layer security (mTLS 1.3) for direct peer-to-peer streaming. Approach B implements application-layer security (Encrypted Envelope) via an untrusted HTTP broker. This README serves as a guide for understanding, setting up, and running both implementations.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Prerequisites](#2-prerequisites)
3. [Setup and Initialization](#3-setup-and-initialization)
4. [Approach A: mTLS 1.3 Direct Streaming](#4-approach-a-mtls-13-direct-streaming)
5. [Approach B: Encrypted Envelope via Untrusted HTTP Broker](#5-approach-b-encrypted-envelope-via-untrusted-http-broker)
6. [Testing and Verification](#6-testing-and-verification)
7. [Security Considerations (CIAA)](#7-security-considerations-ciaa)

---

## 1. Introduction

The objective of this project is to transfer a large file securely between a sender and a receiver. The system must guarantee:
- **Confidentiality:** Data cannot be read by unauthorized parties.
- **Integrity:** Data cannot be modified in transit without detection.
- **Authentication:** Both sender and receiver identities are verified.
- **Availability:** The system can recover from network interruptions (e.g., resumable transfers).

To explore different security paradigms, two distinct architectures are implemented:
- **Approach A:** Relies on the transport layer (TLS 1.3) with mutual authentication (mTLS).
- **Approach B:** Relies on the application layer, encrypting and signing data before uploading it to an untrusted broker.

---

## 2. Prerequisites

- Python 3.8+ (or newer)
- `make` utility
- OpenSSL (for generating certificates)
- Standard Unix utilities (`shasum`, `bash`)

---

## 3. Setup and Initialization

Before running either approach, you must generate the necessary cryptographic materials and a test file.

### 3.1 Generate Cryptographic Keys and Certificates

Run the following commands to generate the required keys and certificates for both approaches:

```bash
# Generate mTLS certificates for Approach A
make certs

# Generate Ed25519 and X25519 keys for Approach B
make keys
```

### 3.2 Generate the Test File

Create a test file to be transferred. The `Makefile` generates a 64 MB test file of random bytes by default for fast testing, but the system is designed to handle files up to 4 GB.

```bash
make testfile
```

---

## 4. Approach A: mTLS 1.3 Direct Streaming

**Architecture:** Direct peer-to-peer connection where the receiver acts as a TLS server and the sender as a TLS client. Both authenticate each other using certificates signed by a shared project Certificate Authority (CA).

### 4.1 Running the Receiver (Server)

Start the receiver first. It will listen for incoming mTLS connections.

```bash
python -m approach_a_mtls.receiver --bind 127.0.0.1:9443 --out ./recv_a/
```

### 4.2 Running the Sender (Client)

In a separate terminal, start the sender to connect to the receiver and stream the file.

```bash
python -m approach_a_mtls.sender --connect 127.0.0.1:9443 --file ./testfile.bin
```

---

## 5. Approach B: Encrypted Envelope via Untrusted HTTP Broker

**Architecture:** The sender encrypts the file into independent 4 MB chunks, signs a manifest, and uploads them to a plain HTTP broker. The broker is untrusted and only sees ciphertext. The receiver downloads the chunks, verifies the signatures, and decrypts the file.

### 5.1 Running the Untrusted Broker

Start the HTTP broker. This acts as the intermediary storage.

```bash
python -m approach_b_envelope.broker --bind 127.0.0.1:9080 --store ./broker_store/
```

### 5.2 Running the Sender (Uploader)

In a separate terminal, encrypt and upload the file to the broker.

```bash
python -m approach_b_envelope.sender --broker http://127.0.0.1:9080 --file ./testfile.bin
```

### 5.3 Running the Receiver (Downloader)

Once uploaded (or concurrently), start the receiver to download, verify, and decrypt the file.

```bash
python -m approach_b_envelope.receiver --broker http://127.0.0.1:9080 --out ./recv_b/testfile.bin
```

---

## 6. Testing and Verification

After the transfer completes (using either approach), verify the integrity of the transferred file by comparing its SHA-256 hash with the original file.

**For Approach A:**
```bash
shasum -a 256 ./testfile.bin ./recv_a/testfile.bin
```

**For Approach B:**
```bash
shasum -a 256 ./testfile.bin ./recv_b/testfile.bin
```
*Both hashes must match exactly.*

---

## 7. Security Considerations (CIAA)

### 7.1 Approach A (mTLS)
- **Confidentiality:** TLS 1.3 encrypts the stream with an AEAD cipher (e.g., AES-GCM).
- **Integrity:** TLS record authentication catches network tampering. A final application-layer SHA-256 hash detects logical truncation.
- **Authentication:** mTLS proves both sender and receiver identities using leaf certificates signed by the pinned CA. Fails closed on bad certificates.
- **Availability:** Application-level resume logic allows the transfer to continue from the last offset after a disconnect.

### 7.2 Approach B (Envelope)
- **Confidentiality:** The file is encrypted locally using an ephemeral file key derived via X25519. The broker only sees ciphertext.
- **Integrity:** AES-GCM tags detect chunk tampering. A signed manifest ensures chunks are not swapped, and an atomic `.tmp` rename guarantees no partial corrupt files are left on disk.
- **Authentication:** The manifest is signed by the Sender's Ed25519 key. Only the true Receiver's X25519 key can derive the decryption key.
- **Availability:** Independent 4 MB chunks are retrieved via HTTP. The receiver can resume downloading missing chunks if interrupted.
