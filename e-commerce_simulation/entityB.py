# Import necessary modules
import base64
import sys
import ecc
from flask import Flask, request


# This function provides a user interface to select the ECC parameters.
def select_ecc_params():
    # The loop continues until the user inputs a valid option.
    while True:
        # Present options for the type of ECC parameters to use.
        print("\nSelect the kind of ECC parameters to use:")
        print("1. Optimized by GA")
        print("2. Optimized by PSO")
        print("3. secp256k1")
        print("4. brainpoolP256r1")
        print("5. Exit the simulation")
        option = input("\nEnter the option (1 to 5): ")
        if option in ["1", "2", "3", "4"]:
            # If a valid option is selected, it is returned for further use.
            return option
        elif option == "5":
            # If option 5 is selected, the program is terminated.
            sys.exit("Exiting the simulation.")
        else:
            # If the input is not valid, the user is prompted to input again.
            print("Incorrect option. Please enter a number between 1 and 5.")


# Application Initialization
app = Flask(__name__) # Create a new Flask application
chosen_params = select_ecc_params() # Type of ECC parameters to be used chosen by the user
params = ecc.initialize_params(chosen_params) # Initialize ECC parameters by calling select_ecc_params function that allows the user to choose the ECC parameters they want to use.
private_key = ecc.generate_private_key(params) # Generate the private key for the elliptic curve cryptography
public_key = ecc.generate_public_key(private_key, params) # Generate the corresponding public key
private_key_ecdh_B = ecc.generate_private_key(params) # Generate a private key for ECDH (Elliptic-curve Diffie-Hellman) protocol in Entity B Server (simulated ERP), used for secure key exchange
public_key_ecdh_B = ecc.generate_public_key(private_key_ecdh_B, params) # Generate the corresponding public key for ECDH (Elliptic-curve Diffie-Hellman) protocol in Entity B, used for secure key exchange
hmac_key = None # Initialize HMAC (Hash-based Message Authentication Code) key to None
message_counter = 0 # Initialize the counter for the received messages


# Route handlers

# This route handles POST requests sent to the '/order' endpoint
@app.route('/order', methods=['POST'])
def decrypt_endpoint():
    global message_counter, hmac_key  # Declare global variables to update them within this function

    # Extract the JSON data from the incoming HTTP POST request from Entity A (emulated e-commerce)
    data = request.get_json()

    # Decrypt the message and verify the HMAC
    is_hmac_valid, decrypted_message = decrypt_order_message(data)

    # If HMAC verification fails, return an error message to the sender Entity A (emulated e-commerce)
    if not is_hmac_valid:
        return {"status": "error", "message": "HMAC verification failed"}

    # If HMAC verification succeeds, increment the message counter and print the transaction details
    message_counter += 1
    print(f"\n\nTransaction {message_counter}:")
    print(f"Encrypted message: {data['encrypted_message']}")

    if decrypted_message is None:
        print("Decryption failed.")
    else:
        print(f"Decrypted message: {decrypted_message}")

    # Return a success status response to the sender Entity A (emulated e-commerce)
    return {'status': 'success'}

# This route handles GET requests sent to the '/public-key' endpoint and returns the public key to Entity A (emulated e-commerce)
@app.route('/public-key', methods=['GET'])
def public_key_endpoint():
    return {"public_key": {"x": public_key.x, "y": public_key.y}}

# This route handles GET requests sent to the '/public-key-ecdh' endpoint and returns the ECDH public key
@app.route('/public-key-ecdh', methods=['GET'])
def public_key_ecdh_endpoint():
    return {"public_key_ecdh": {"x": public_key_ecdh_B.x, "y": public_key_ecdh_B.y}}

# This route handles GET requests sent to the '/get-params' endpoint and returns the selected option for ECC parameters.
    # 1. Optimized by GA
    # 2. Optimized by PSO
    # 3. secp256k1
    # 4. brainpoolP256r1
@app.route('/get-params', methods=['GET'])
def get_params_endpoint():
    return {"params": chosen_params}

# Helper Functions
def decrypt_order_message(data):
    """
    This function handles the decryption of the order message and the validation of its HMAC.
    Args:
        data (dict): The incoming order data that contains the encrypted message from Entity A (emulated e-commerce), HMAC, and keys.
    Returns:
        is_hmac_valid (bool): A flag indicating whether the HMAC validation was successful.
        decrypted_message (str): The decrypted message content.
    """

    global hmac_key  # Define hmac_key as global so it can be accessed outside this function

    # Extract the first part of the encrypted message from the incoming data and convert it to an ECPoint
    C1_data = data['C1']
    C1 = ecc.ECPoint(int(C1_data['x']), int(C1_data['y']))

    # Extract the encrypted message from the incoming data
    encrypted_message = data['encrypted_message']

    # Extract and decode the HMAC from the incoming data
    received_hmac = base64.b64decode(data['hmac'])

    # Decrypt the message using our ECC private key and the first part of the encrypted message
    try:
        decrypted_message = ecc.decrypt_message(C1, encrypted_message, private_key, params)
    except Exception as e:
        print(f"An error occurred during decryption: {str(e)}")
        decrypted_message = None


    # Extract Entity A's ECDH public key from the incoming data (emulated e-commerce) and convert it to an ECPoint
    public_key_ecdh_A = ecc.ECPoint(data['public_key_ecdh_A']['x'], data['public_key_ecdh_A']['y'])

    # Compute the shared secret by performing scalar multiplication between Entity A's ECDH public key and Entity B's ECDH private key
    shared_secret = ecc.ec_scalar_multiplication(public_key_ecdh_A, private_key_ecdh_B, params)

    # Convert the x-coordinate of the shared secret to bytes and use it as the HMAC key
    hmac_key = str(shared_secret.x).encode('utf-8')

    # Verify the received HMAC using the computed HMAC key, decrypted message and the received HMAC
    is_hmac_valid = ecc.verify_hmac(hmac_key, decrypted_message, received_hmac)

    # Print a success message if the HMAC verification is valid, otherwise print a failure message
    if is_hmac_valid:
        print("HMAC verification succeeded.")
    else:
        print("HMAC verification failed.")
    
    # Return the results of the HMAC verification and the decrypted message
    return is_hmac_valid, decrypted_message



# Run the server
if __name__ == "__main__":
    app.run(host='localhost', port=5000)
