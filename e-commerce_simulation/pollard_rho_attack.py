# Import necessary libraries
import sys
import requests
import ecc
import gmpy2
from multiprocessing import Pool, Manager
import random

def pollard_rho_attack(init_value, G, public_key, params, manager_dict):
    """
    This function performs Pollard's rho attack in the ECC context.
    
    Args:
        init_value (int): The initial value used for the tortoise and hare points.
        G (ECPoint): The generator point on the elliptic curve.
        public_key (ECPoint): The public key of the entity being attacked.
        params (ECParams): The parameters of the elliptic curve.
        manager_dict (dict): A dictionary shared across processes.
        
    Returns:
        None. However, this function can modify the shared dictionary to indicate that the private key has been found.
    """

    # Print a message indicating the start of the attack and the initial value used
    print(f"Starting pollard_rho_attack with initial value {init_value}")
    
    # Initialize tortoise and hare points by performing scalar multiplication on the generator point
    tortoise = ecc.ec_scalar_multiplication(G, init_value, params)
    hare = ecc.ec_scalar_multiplication(G, init_value, params)

    # Initialize scalar values for the tortoise and hare points
    tortoise_scalar = hare_scalar = init_value

    # Iterate over a range of values and update the tortoise and hare points and their corresponding scalar values
    for i in range(1, 2*params.n+1): #number of iterations
        # Updating tortoise and hare points and their corresponding scalar values
        tortoise, tortoise_scalar = step(tortoise, tortoise_scalar, G, public_key, params)
        hare, hare_scalar = step(hare, hare_scalar, G, public_key, params)
        hare, hare_scalar = step(hare, hare_scalar, G, public_key, params)

        # Print iteration details
        print(f"Iteration {i}: tortoise={tortoise}, hare={hare}, tortoise_scalar={tortoise_scalar}, hare_scalar={hare_scalar}")
        
        # If tortoise and hare points collide and tortoise is not None, proceed with collision handling
        if tortoise == hare and tortoise is not None:
            # Calculate the difference of the scalar values and find its modulo with respect to n
            scalar_difference = gmpy2.f_mod((tortoise_scalar - hare_scalar), params.n)
            
            # If the scalar difference is 0, a useless collision has occurred. Continue to the next iteration
            if scalar_difference == 0:
                print(f"Useless collision detected at iteration {i} with initial value {init_value}")
                continue

            # Calculate the multiplicative inverse of the scalar difference
            scalar_difference_inverse = gmpy2.invert(scalar_difference, params.n)

            # Calculate the secret key
            secret_key = gmpy2.f_mod((scalar_difference_inverse * hare_scalar), params.n)
            
            # Lock the shared dictionary and update the 'found_flag' if it is False
            with manager_dict['lock']:
                if not manager_dict['found_flag']:
                    manager_dict['found_flag'] = True
                    # Print the found secret key
                    print(f'Private key found by process starting at {init_value}: {secret_key}')
            break

        # If the secret key has been found, break the loop
        if manager_dict['found_flag']:
            break

    # If the secret key has not been found, print a message indicating the same
    if not manager_dict['found_flag']:
        print(f"Finished pollard_rho_attack with initial value {init_value}, but no private key found.")
    else:
        print(f"Finished pollard_rho_attack with initial value {init_value}")


def step(point, scalar, G, public_key, params):
    """
    This function determines the next step in Pollard's rho attack.
    Define a function to move the tortoise/hare and update their scalar.
    
    Args:
        point (ECPoint): The current point in the walk.
        scalar (int): The scalar corresponding to the current point.
        G (ECPoint): The generator point on the elliptic curve.
        public_key (ECPoint): The public key of the entity being attacked.
        params (ECParams): The parameters of the elliptic curve.
        
    Returns:
        A tuple containing the new point and its corresponding scalar.
    """

    # If point is at infinity, return None and 0
    if point is None or point.inf:
        return None, 0
    # If x-coordinate of point modulo 3 equals 0, double the point and return updated point and scalar
    elif point.x % 3 == 0:
        temp_point = ecc.ec_addition(point, point, params)
        # If addition operation resulted in None or point at infinity, print an error message and return None and 0
        if temp_point is None or temp_point.inf:
            print("Error: Addition returned None or point at infinity.")
            return None, 0
        return temp_point, gmpy2.f_mod((scalar * 2), params.n)
    # If x-coordinate of point modulo 3 equals 1, add the point and public key, return updated point and scalar
    elif point.x % 3 == 1:
        temp_point = ecc.ec_addition(point, public_key, params)
        # If addition operation resulted in None or point at infinity, print an error message and return None and 0
        if temp_point is None or temp_point.inf:
            print("Error: Addition returned None or point at infinity.")
            return None, 0
        return temp_point, gmpy2.f_mod((scalar + scalar), params.n)
    # Otherwise, add the point and generator point G, return updated point and scalar
    else:
        temp_point = ecc.ec_addition(point, G, params)
        # If addition operation resulted in None or point at infinity, print an error message and return None and 0
        if temp_point is None or temp_point.inf:
            print("Error: Addition returned None or point at infinity.")
            return None, 0
        return temp_point, gmpy2.f_mod((scalar + 1), params.n)


def get_ecc_params_from_server():
    """
    This function retrieves the parameters of the elliptic curve from the server.
    
    Returns:
        A dictionary containing the parameters of the elliptic curve.
    """

    # Define the server URL
    server_url = 'http://localhost:5000/get-params'

    # Send a GET request to the server and store the response
    response = requests.get(server_url)

    # If the response status code is 200 (indicating a successful request), return the ECC parameters
    if response.status_code == 200:
        option = response.json()['params']
        return option
    else:
        # Otherwise, print an error message and exit the program
        print("Error occurred while retrieving ECC parameters from server.")
        sys.exit("Exiting the simulation.")


def get_public_key_from_entityB():
    """
    This function retrieves the public key of Entity B.
    
    Returns:
        The public key of Entity B as an ECPoint.
    """

    # Define the URL for Entity B's public key
    entityB_url_public_key = 'http://localhost:5000/public-key'

    # Send a GET request to the URL and store the response
    response = requests.get(entityB_url_public_key)

    # If the response status code is 200 (indicating a successful request), return the public key
    if response.status_code == 200:
        public_key_data = response.json()['public_key']
        public_key = ecc.ECPoint(public_key_data['x'], public_key_data['y'])
        return public_key
    else:
        # Otherwise, print an error message and exit the program
        print("Error occurred while retrieving public_key from Entity B.")
        sys.exit("Exiting the simulation.")


def pollards_rho_attack_on_entityB(params):

    """
    This function carries out Pollard's rho attack on Entity B.
    This function takes the elliptic curve parameters as argument.
    
    Args:
        params (ECParams): The parameters of the elliptic curve.
    """

    # Retrieve Entity B's public key
    public_key = get_public_key_from_entityB()

    # Create a manager object to manage a shared dictionary across processes
    manager = Manager()
    manager_dict = manager.dict()

    # Initialize the 'found_flag' in the dictionary to False
    manager_dict['found_flag'] = False

    # Create a lock in the dictionary to prevent race conditions
    manager_dict['lock'] = manager.Lock()

    # Create a pool of 4 processes and carry out the Pollard's rho attack in parallel
    with Pool(processes=4) as pool:
        pool.starmap(pollard_rho_attack, [(random.randint(1, params.n), params.G, public_key, params, manager_dict) for _ in range(4)])


def main():
    """
    The main function that carries out the entire process. It retrieves the ECC parameters from the server,
    initializes these parameters, and then performs Pollard's rho attack on Entity A.
    """
    # Retrieve the ECC parameters from the server
    option = get_ecc_params_from_server()

    # Initialize the elliptic curve parameters
    params = ecc.initialize_params(option)

    # Carry out Pollard's rho attack on Entity B
    pollards_rho_attack_on_entityB(params)

# Call the main function if the script is run directly
if __name__ == "__main__":
    main()
