import sys
import time
import random
import requests
import base64
import ecc
import pandas as pd
import logging
import os

# Set up logging with a basic configuration
logging.basicConfig(level=logging.INFO)

# URL of the server (simulated ERP) to which we'll be sending requests. 
# In this case, it's a local server running on port 5000.
SERVER_URL = 'http://localhost:5000'  

# This endpoint is used to get the selected option for ECC parameters required for the ECC (Elliptic Curve Cryptography).
# 1. Optimized by GA
# 2. Optimized by PSO
# 3. secp256k1
# 4. brainpoolP256r1
GET_PARAMS_ENDPOINT = '/get-params'  

# Endpoint to get the public key. 
# This endpoint is used to get the public key for encryption from the server (simulated ERP).
GET_PUBLIC_KEY_ENDPOINT = '/public-key'

# Endpoint to get the ECDH public key.
# This endpoint is used to get the ECDH (Elliptic Curve Diffie Hellman) public key from the server (simulated ERP) for shared secret computation.
GET_PUBLIC_KEY_ECDH_ENDPOINT = '/public-key-ecdh'  

# Endpoint to send data to the server (simulated ERP) as a order.
# This endpoint is used to send the encrypted messages to the server (simulated ERP).
ORDER_ENDPOINT = '/order' 

# File path to the excel file containing the retail data (Orders Dataset).
# This file is used to generate the messages to be sent to the server (simulated ERP).
EXCEL_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'Online_Retail.xlsx')

# Check if the file exists
try:
    with open(EXCEL_FILE_PATH, 'r'):
        pass  # Do nothing, just checking if the file can be opened
except FileNotFoundError:
    print(f"Error: The file {EXCEL_FILE_PATH} does not exist. Please make sure the data folder and the .xlsx file are in the correct location.")
    sys.exit(1)  # Exit the program with an error code

class ServerConnection:
    """
    Class to manage server (simulated ERP) connections.
    """
    def __init__(self, server_url):
        """
        Initialize a new ServerConnection.

        :param server_url: URL of the server (simulated ERP) to connect to.
        """
        self.server_url = server_url

    def get(self, endpoint):
        """
        Send a GET request to the server (simulated ERP).

        :param endpoint: Server endpoint to send the request to.
        :return: The server's response as a dictionary.
        """
        try:
            response = requests.get(self.server_url + endpoint)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as err:
            logging.error(f"HTTP error occurred: {err}")
            sys.exit("Exiting the simulation.")
        except Exception as err:
            logging.error(f"An error occurred: {err}")
            sys.exit("Exiting the simulation.")
    
    def post(self, endpoint, data):
        """
        Send a POST request to the server (simulated ERP).

        :param endpoint: Server endpoint to send the request to.
        :param data: Data to send in the request body.
        :return: The server's response as a dictionary.
        """
        try:
            response = requests.post(self.server_url + endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as err:
            logging.error(f"HTTP error occurred: {err}")
            sys.exit("Exiting the simulation.")
        except Exception as err:
            logging.error(f"An error occurred: {err}")
            sys.exit("Exiting the simulation.")


class ECCParams:
    """
    Class to manage ECC parameters.
    """
    def __init__(self, server_connection):
        """
        Initialize a new ECCParams object.

        :param server_connection: A ServerConnection object.
        """
        self.server_connection = server_connection
        self.params = None

    def initialize_params(self):
        """
        Initialize ECC parameters by requesting them from the server (simulated ERP).
        This is used to get the selected option for ECC parameters required for the ECC (Elliptic Curve Cryptography).
            # 1. Optimized by GA
            # 2. Optimized by PSO
            # 3. secp256k1
            # 4. brainpoolP256r1

        :return: Initialized ECC parameters.
        """
        option = self.server_connection.get(GET_PARAMS_ENDPOINT)['params']
        self.params = ecc.initialize_params(option)
        return self.params


class ECCKeys:
    """
    Class to manage ECC keys.
    """
    def __init__(self, ecc_params):
        """
        Initialize a new ECCKeys object.

        :param ecc_params: ECC parameters.
        """
        self.ecc_params = ecc_params
        self.private_key = None
        self.public_key = None

    def generate_keys(self):
        """
        Generate ECC private and public keys.
        """
        self.private_key = ecc.generate_private_key(self.ecc_params)
        self.public_key = ecc.generate_public_key(self.private_key, self.ecc_params)


class RetailMessage:
    """
    Class to generate retail messages from an Excel file.
    """
    def __init__(self, excel_file_path):
        """
        Initialize a new RetailMessage object.

        :param excel_file_path: Path to the Excel file.
        """
        self.excel_file_path = excel_file_path
        self.df = pd.read_excel(self.excel_file_path)

    def generate_message(self):
        """
        Generate a random message from the retail dataset.

        This function selects a random row from the orders dataset and then 
        retrieves a subset of rows that have the same 'OrderNo' and are in close proximity to the selected row.
        The selected subset of rows is then converted to a JSON string.

        :return: The message as a JSON string.
        """
        # Pick a random row from the dataframe.
        random_row = self.df.sample(n=1)
        # Get the index of the selected row.
        random_row_index = random_row.index[0]
        # Get the 'OrderNo' of the selected row.
        column_a_value = random_row['OrderNo'].iloc[0]

        # Set a range of indices within which we want to find rows with the same 'OrderNo'.
        # We select a window of size 7, centered around the index of the selected row.
        lower_bound = max(0, random_row_index - 3)
        upper_bound = min(len(self.df), random_row_index + 4)

        # Get all rows within the set range that have the same 'OrderNo' as the selected row.
        rows_with_same_value = self.df[
            (self.df['OrderNo'] == column_a_value) &
            (self.df.index >= lower_bound) &
            (self.df.index <= upper_bound)
        ]

        # Log the selected row and the selected subset of rows.
        logging.info(f"\nRandom row:\n{random_row}")
        logging.info(f"\nRows with the same value in column A within the search window:\n{rows_with_same_value}")

        # Convert the selected subset of rows to a JSON string and return it.
        return self.create_json_message(rows_with_same_value)

    @staticmethod
    def create_json_message(data):
        """
        Convert a pandas DataFrame to a JSON string.

        This function is used to convert the selected subset of rows to a JSON string.
        The JSON string is used as the message to be sent to the server (simulated ERP).

        :param data: DataFrame to convert.
        :return: The DataFrame as a JSON string.
        """
        # Convert the dataframe to a JSON string.
        json_message = data.to_json(orient='records')
        # Log the generated JSON message.
        logging.debug(f"\nJSON message:\n{json_message}") # displayed only if log level is "debug"
        # Return the JSON message.
        return json_message

class TransactionManager:
    """
    Class to manage transactions.
    
    This class is responsible for sending messages to the server (simulated ERP) and receiving responses.
    """
    def __init__(self, server_connection, ecc_keys, message_generator):
        """
        Initialize a new TransactionManager object.

        This function is the constructor for the TransactionManager class.
        It initializes the TransactionManager with a server connection, ECC keys, and a message generator.

        :param server_connection: A ServerConnection object.
        :param ecc_keys: An ECCKeys object.
        :param message_generator: A RetailMessage object.
        """
        # The ServerConnection object used to communicate with the server (simulated ERP).
        self.server_connection = server_connection
        # The ECCKeys object used to encrypt the messages.
        self.ecc_keys = ecc_keys
        # The RetailMessage object used to generate messages.
        self.message_generator = message_generator
        # The key used to generate the HMAC.
        self.hmac_key = None
        # The end time for the transactions. Transactions will be performed continuously until this time.
        self.end_time = time.time() + 60
        # The number of transactions that have been performed.
        self.message_counter = 0

    def run_transactions(self):
        """
        Run transactions until a certain amount of time has passed.

        This function continuously performs transactions until the end time has been reached.
        After each transaction, the function waits for a random amount of time between 0 and 3 seconds.
        """
        # While the current time is less than the end time, continue performing transactions.
        while time.time() < self.end_time:
            # Perform a single transaction.
            self.perform_transaction()
            # Wait for a random amount of time between 0 and 3 seconds before the next transaction.
            time.sleep(random.uniform(0, 3))


    def perform_transaction(self):
        """
        Perform a single transaction.
        This method is responsible for preparing and sending an encrypted message 
        to the server (simulated ERP), then receiving the server's response. It uses ECC to handle 
        the encryption and generates a HMAC for message authentication.
        """
        
        # Increment the message counter, used to track the number of messages sent.
        self.message_counter += 1
        
        # Request the public key from the server (simulated ERP), which will be used to encrypt the message.
        public_key_data = self.server_connection.get(GET_PUBLIC_KEY_ENDPOINT)['public_key']
        
        # Construct an ECPoint (an object representing a point on an elliptic curve) 
        # using the coordinates received from the server (simulated ERP).
        public_key = ecc.ECPoint(public_key_data['x'], public_key_data['y'])

        # Log the transaction number.
        logging.info(f"\n\nTransaction {self.message_counter}:")
        
        # Generate a random message from the retail dataset.
        message = self.message_generator.generate_message()

        # Request the public key for Elliptic Curve Diffie-Hellman (ECDH) from the server (simulated ERP).
        # ECDH is a key agreement protocol that allows two parties to establish a shared 
        # secret over an insecure channel.
        response_data = self.server_connection.get(GET_PUBLIC_KEY_ECDH_ENDPOINT)['public_key_ecdh']
        public_key_ecdh_B = ecc.ECPoint(int(response_data['x']), int(response_data['y']))

        # Calculate the shared secret using ECDH. The result (shared_secret) is a point 
        # on the elliptic curve.
        shared_secret = ecc.ec_scalar_multiplication(public_key_ecdh_B, self.ecc_keys.private_key, self.ecc_keys.ecc_params)
        
        # Convert the x-coordinate of the shared secret to a string and encode it to bytes. 
        # This will be used as the HMAC key.
        self.hmac_key = str(shared_secret.x).encode('utf-8')

        # Encrypt the message using the server's public key. The function returns two parts: 
        # C1, a point on the elliptic curve representing part of the encrypted message, 
        # and encrypted_message, the rest of the encrypted message.
        C1, encrypted_message = ecc.encrypt_message(message, public_key, self.ecc_keys.ecc_params)
        
        # Generate a HMAC of the message using the shared secret as the key. This will 
        # allow the server (simulated ERP) to verify the integrity and authenticity of the message.
        hmac_A = ecc.generate_hmac(self.hmac_key, message)

        # Send a POST request to the server (simulated ERP) with the encrypted message, HMAC, and some other related 
        # information. The server (simulated ERP) will decrypt the message, verify the HMAC, and then 
        # send a response.
        response = self.server_connection.post(ORDER_ENDPOINT, {
            "C1": {"x": C1.x, "y": C1.y},
            "encrypted_message": encrypted_message,
            "hmac": base64.b64encode(hmac_A).decode(),
            "public_key_ecdh_A": {"x": self.ecc_keys.public_key.x, "y": self.ecc_keys.public_key.y}
        })

        # Log the original message, encrypted message, HMAC, and server (simulated ERP) response for debugging.
        logging.info(f"\nOriginal message: {message}")
        logging.debug(f"\nEncrypted message: {encrypted_message}") # displayed only if log level is "debug"
        logging.info(f"\nHMAC: {base64.b64encode(hmac_A).decode()}")
        logging.info(f'\nResponse from server: {response}')


def main():
    """
    Main function to run the script.
    
    This function is responsible for establishing the initial connection with the server (simulated ERP), 
    setting up ECC parameters (with the selected option from the server (simulated ERP)) and keys, and initiating the retail message generator. 
    It then starts the transaction manager to run transactions continuously.
    """
    
    # Establish a connection with the server (simulated ERP) at SERVER_URL. 
    # This connection will be used to communicate with the server throughout the script.
    server_connection = ServerConnection(SERVER_URL)
    
    # Initialize ECC parameters by asking the server (simulated ERP) for the recommended parameters.
    # This is important for making sure the client and server are using the same elliptic curve.
    ecc_params = ECCParams(server_connection).initialize_params()
    
    # Generate ECC keys (a private key and a corresponding public key) using the 
    # ECC parameters that were just initialized.
    ecc_keys = ECCKeys(ecc_params)
    ecc_keys.generate_keys()
    
    # Initialize the retail message generator with the provided Excel file path (Orders Dataset).
    # This will be used to generate the messages that will be sent to the server (simulated ERP).
    message_generator = RetailMessage(EXCEL_FILE_PATH)

    # Initialize the transaction manager with the server (simulated ERP) connection, ECC keys, and the 
    # retail message generator. The transaction manager is responsible for sending 
    # encrypted messages to the server (simulated ERP) and receiving responses.
    transaction_manager = TransactionManager(server_connection, ecc_keys, message_generator)
    
    # Start the transaction manager, which will continuously perform transactions 
    # (sending messages and receiving responses) until it is stopped.
    transaction_manager.run_transactions()


if __name__ == "__main__":
    """
    Entry point of the script. Call the main function.
    """
    main()
