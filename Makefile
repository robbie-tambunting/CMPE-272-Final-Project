CERTS_DIR = certs

.PHONY: certs keys testfile clean

# Generate project CA + sender + receiver leaf certs (mTLS demo)
certs:
	mkdir -p $(CERTS_DIR)
	# CA
	openssl genrsa -out $(CERTS_DIR)/ca.key 4096
	openssl req -new -x509 -key $(CERTS_DIR)/ca.key -out $(CERTS_DIR)/ca.crt \
	    -days 3650 -subj "/CN=cmpe272-CA"
	# Sender leaf cert
	openssl genrsa -out $(CERTS_DIR)/sender.key 2048
	openssl req -new -key $(CERTS_DIR)/sender.key -out $(CERTS_DIR)/sender.csr \
	    -subj "/CN=cmpe272-sender"
	openssl x509 -req -in $(CERTS_DIR)/sender.csr \
	    -CA $(CERTS_DIR)/ca.crt -CAkey $(CERTS_DIR)/ca.key -CAcreateserial \
	    -out $(CERTS_DIR)/sender.crt -days 365
	# Receiver leaf cert (CN matches SERVER_HOSTNAME used by sender TLS verify)
	openssl genrsa -out $(CERTS_DIR)/receiver.key 2048
	openssl req -new -key $(CERTS_DIR)/receiver.key -out $(CERTS_DIR)/receiver.csr \
	    -subj "/CN=cmpe272-receiver"
	openssl x509 -req -in $(CERTS_DIR)/receiver.csr \
	    -CA $(CERTS_DIR)/ca.crt -CAkey $(CERTS_DIR)/ca.key -CAcreateserial \
	    -out $(CERTS_DIR)/receiver.crt -days 365
	rm -f $(CERTS_DIR)/*.csr $(CERTS_DIR)/*.srl
	@echo "Certs written to $(CERTS_DIR)/"

# Generate sender Ed25519 + receiver X25519 keypairs (Approach B)
keys:
	python3 -m approach_b_envelope.keygen

# Create a 64 MB test file (16 × 4 MB chunks — fast, exercises chunking)
testfile:
	python3 -c "import os; open('testfile.bin','wb').write(os.urandom(64*1024*1024))"
	@echo "testfile.bin created (64 MB)"

clean:
	rm -rf $(CERTS_DIR) keys/ testfile.bin recv_a/ recv_b/ broker_store/
