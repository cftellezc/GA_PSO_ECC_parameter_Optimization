# Import required libraries
from sympy.ntheory import isprime  # To check if a number is prime
from tinyec import ec  # Elliptic curve library
from Crypto.Util.number import getPrime  # Generate prime numbers
import signal
import logging  # Import the logging library
import random  # To generate random numbers
import time
import math

BITS_PRIME_SIZE = 256 #size of the prime in bits - Generate a n-bit prime number    
TIMEOUT_SECONDS = 96000 # Set values ​​less than 30 seconds for 16-bit prime numbers or less
POLLARDS_RHO_TRIALS = 20 # Number of trials for the Pollard's Rho function.
POLLARDS_RHO_MAX_ITER = 10**2 # Maximum iterations for each trial in the Pollard's Rho function.

# Add an exception for when no generator point is found
class NoGeneratorPointException(Exception):
    pass

def get_prime_for_p():
    return getPrime(BITS_PRIME_SIZE) #Generate a BITS_PRIME_SIZE-bit prime number for prime number p

def find_generator_point(a, b, p):
    # Loop through all possible x-coordinates in the finite field (up to prime number 'p')
    for x in range(p):
        # Compute the RHS of the elliptic curve equation (y^2 = x^3 + ax + b) modulo p
        rhs = (x**3 + a * x + b) % p

        # Check if RHS is a quadratic residue using the Legendre symbol. If it is,
        # it means there exists a y such that y^2 = RHS (mod p)
        if legendre_symbol(rhs, p) == 1:  # RHS is a quadratic residue
            # Compute the square root directly instead of looping through all y-values
            y = tonelli_shanks(rhs, p)
            return (x, y)

    # If we've tried all possible x and y in the field and haven't found a point on the curve, raise an exception
    raise NoGeneratorPointException


def legendre_symbol(a, p):
    """
    The Legendre symbol is a mathematical function that gives information about whether a number
    'a' is a quadratic residue modulo 'p'. The pow function uses fast exponentiation (O(log p)) to 
    compute a^((p - 1) / 2) mod p. The result is either 1 (which indicates that 'a' is a quadratic residue)
    or p - 1 (which indicates that 'a' is a quadratic non-residue).
    """
    ls = pow(a, (p - 1) // 2, p)  # Fast exponentiation to compute the Legendre symbol
    # Return the Legendre symbol as -1 if it equals p - 1 (indicating 'a' is a non-residue), and as ls otherwise
    return -1 if ls == p - 1 else ls

def tonelli_shanks(n, p):
    """
    Tonelli-Shanks algorithm for finding square roots modulo a prime number.
    This method finds a number r such that r^2 = n (mod p).
    Note that n must be a quadratic residue modulo p, i.e. there must exist some r such that r^2 = n (mod p).
    If such an r does not exist, the function will enter an infinite loop.
    The function will return one solution r. The other solution is -r (mod p).
    """
    # Ensure that n is a quadratic residue modulo p
    assert legendre_symbol(n, p) == 1, "n is not a quadratic residue modulo p"
    
    # Write (p - 1) as 2^s * q with q odd (by factoring out powers of 2 from p - 1)
    q = p - 1
    s = 0
    while q % 2 == 0:
        q //= 2
        s += 1
    
    # If s = 1, then we can solve the problem directly
    # (this is a special case of the more general algorithm below)
    if s == 1:
        return pow(n, (p + 1) // 4, p)
    
    # Find a quadratic non-residue z by brute-force search
    for z in range(2, p):
        if legendre_symbol(z, p) == -1:
            break
    
    # Variables initialization
    m = s
    c = pow(z, q, p)
    t = pow(n, q, p)
    r = pow(n, (q + 1) // 2, p)
    
    # Repeat until we find a solution
    while t != 1:
        # Find the smallest i such that t^(2^i) = 1
        i = 0
        t_i = t
        while t_i != 1:
            t_i = pow(t_i, 2, p)
            i += 1
        
        # Update variables
        b = pow(c, pow(2, m - i - 1), p)
        r = r * b % p
        t = t * b * b % p
        c = b * b % p
        m = i
    
    return r

# Check if the elliptic curve is singular
def is_singular(a, b, p):
    discriminant = (4*a**3 + 27*b**2) % p  # Calculate the discriminant
    return discriminant == 0  # The curve is singular if the discriminant is zero

# Check if the elliptic curve is anomalous
def is_anomalous(p, n):
    return p == n  # The curve is anomalous if the order of the curve equals its characteristic

# Check if the elliptic curve is supersingular
def is_supersingular(p, n):
    if p in [2, 3] or not isprime(p):
        return False
    return (p+1 - n) % p == 0  # The curve is supersingular if p+1-n is divisible by p

# Validate the parameters of the elliptic curve
def validate_curve(a, b, p, G, n, h):
    logging.info("\nValidating the parameters of the elliptic curve")
    logging.info(f"a: {a}, b: {b}, p: {p}, G: {G}, n: {n}, h: {h}")

    # Check if h is less than 1, which would make it invalid.
    if h < 1:
        logging.info("The cofactor h is less than 1, which makes it invalid.")
        return False
    
    if p == 0:
        logging.info("The prime p can't be zero.")
        return False
    elif isinstance(G, tuple) and len(G) == 2:  # Check if G is a tuple of length 2
        # Check if the point G lies on the curve
        x, y = G
        if (y*y - x*x*x - a*x - b) % p != 0:
            logging.info(f"The point G {G} is not on the curve!")
            return False

        # If G lies on the curve, continue with the validation
        try:
            field = ec.SubGroup(p, G, n, h)
        except NoGeneratorPointException:
            logging.info("No generator point found!")
            return False

        curve = ec.Curve(a, b, field, "random_curve")
    else:
        # Handle the case where G is False
        logging.info("Invalid generator point provided. Skipping curve creation.")
        return False

    order = n  # Get the order of the curve  

    if h != field.h:  # Check if the cofactor is correct
        logging.info(f"The cofactor {field.h} does not match the expected cofactor {h}!")
        return False
    
    # Check if n is a prime number: 
    # This check is not necessary for the curve to be secure. However, this will make 
    # the curve less secure against certain attacks.
    #if not isprime(n):
    #   logging.info(f"The order n {n} is not a prime number!")
    #   return False
    
    if is_singular(a, b, p):  # Check if the curve is singular
        logging.info("The curve is singular!")
        return False
    if is_anomalous(p, order):  # Check if the curve is anomalous
        logging.info("The curve is anomalous!")
        return False
    if is_supersingular(p, order):  # Check if the curve is supersingular
        logging.info("The curve is supersingular!")
        return False
    return True  # If all checks pass, the curve is valid


# Function to generate the parameters for an elliptic curve
def generate_curve():
    def handler(signum, frame):
        raise TimeoutError()
    
    signal.signal(signal.SIGALRM, handler)

    while True:
        p = get_prime_for_p()  # Generate a prime number p
        # Generate two random numbers 'a' and 'b' which are coefficients of the elliptic curve. The loop ensures the curve is not singular
        while True:
            logging.info("Generate two random numbers 'a' and 'b'")
            a = random.randint(0, p-1)
            b = random.randint(0, p-1)
            logging.info("a: %s", a)
            logging.info("b: %s", b)
            if (4*a**3 + 27*b**2) % p != 0 and not is_singular(a, b, p): # Check condition for non-singularity
                break  

        try:
            signal.alarm(TIMEOUT_SECONDS)  
            # Find a base point 'G' on the elliptic curve. The loop ensures the point lies on the curve
            G = find_generator_point(a, b, p)
            logging.info("G: %s", G)
            signal.alarm(0)  # Disable the alarm after the critical code has been run
            break  # If no exception was raised, break the outer loop as well.
        except (NoGeneratorPointException, TimeoutError):
            continue  # If an exception was raised, continue the outer loop to generate new a, b and p.
        
    # To compute the order of the elliptic curve, a common approach is to use Schoof's algorithm or its variants 
    # (like Schoof-Elkies-Atkin algorithm). However, these algorithms are quite complex
    n = p - 1  # Rough approximation of the order of the curve.
    h = 1  # Cofactor, defaults to 1
    return (a, b, p, G, n, h)  # Return the parameters as a tuple

# Function to add two points on an elliptic curve
def add_points(P, Q, a, p):
    # If P is None, the result is Q
    if P is None:
        return Q
    # If Q is None, the result is P
    elif Q is None:
        return P
    # If P and Q are the same point, calculate the "slope" using the formula for point doubling
    elif P == Q:
        lamb = (3 * P[0]**2 + a) * pow(2 * P[1], p - 2, p)
    # If P and Q are different points, calculate the "slope" using the formula for point addition
    else:
        lamb = (P[1] - Q[1]) * pow(P[0] - Q[0], p - 2, p)

    # Reduce "slope" modulo p
    lamb %= p
    # Compute the x and y coordinates of the result
    x = (lamb**2 - P[0] - Q[0]) % p
    y = (lamb * (P[0] - x) - P[1]) % p
    return (x, y)

# Function for the "double and add" method for elliptic curve point multiplication
def double_and_add(n, P, a, p):
    Q = None
    while n > 0:
        if n % 2 == 1:
            # Add P to Q if the current bit of n is 1
            Q = add_points(Q, P, a, p)
        # Double P
        P = add_points(P, P, a, p)
        # Shift n to the right by one bit
        n //= 2
    return Q

# Function to check if a point is "distinguished", i.e., its x-coordinate has t trailing zeros
def is_distinguished(P, t):
    return P[0] & ((1 << t) - 1) == 0



# Function to evaluate the fitness of a candidate: an individual in the population (GA) or a particle in the swarm (PSO)
def evaluate(candidate):
    # Log start of the evaluation function
    logging.info("Evaluation function to evaluate the fitness")

    # Extract the parameters of the elliptic curve and its order from the individual
    a, b, p, G, n, h = candidate

    # Log the extracted ECC parameters
    logging.info(f"Candidate Parameters: a: {a}, b: {b}, p: {p}, G: {G}, n: {n}, h: {h}")

    # Validate the curve and its parameters, and if they are invalid, return a fitness of 0
    if not validate_curve(a, b, p, G, n, h):
        return 0,

    # Calculate the expected order of the curve and the bounds of Hasse's theorem
    expected_order = p + 1
    lower_bound = expected_order - 2*math.isqrt(p)
    upper_bound = expected_order + 2*math.isqrt(p)

    # Calculate a score based on Hasse's theorem. This score is higher when n is closer to the expected order
    hasse_score = max(0, (upper_bound - abs(n-expected_order))/(upper_bound - lower_bound))

    # Start a timer and attempt Pollard's rho attack on the curve
    start_time = time.time()
    rho_attack_result = pollards_rho_attack(G, a, b, p, expected_order) #instead of sending order n, the expected_order p + 1 is sent
    execution_time = time.time() - start_time
    
    # Convert the execution time of the attack into a score in the range [0,1]. This score is higher for longer execution times
    max_time = 10.0
    min_time = 0.1
    execution_score = max(0, min(1, (execution_time - min_time) / (max_time - min_time)))

    # If the attack was unsuccessful, give a bonus to the score
    attack_resistance_score = 1 if rho_attack_result is None else 0
    # Log the Pollard's rho attack score
    logging.info("Pollard's rho attack: %s", attack_resistance_score)
    
    # Calculate the final fitness score, which is a weighted sum of the logarithm of the order of the curve, 
    # the Hasse score (weighted by the logarithm of the order), the execution score, and the attack resistance score
    fitness = 0.4 * math.log(n) + 0.2 * hasse_score * math.log(n) + 0.2 * execution_score + 0.2 * attack_resistance_score

    # Return the final fitness score
    return fitness,


# Function to perform the Pollard's rho attack on an elliptic curve
def pollards_rho_attack(G, a, b, p, order, t=POLLARDS_RHO_TRIALS, max_iterations=POLLARDS_RHO_MAX_ITER):
    #The t parameter determines how often a point is considered "distinguished" and therefore 
    #stored for collision checking. A lower t value will result in more points being stored and 
    #therefore a higher chance of finding a collision, but at the cost of increased memory usage.

    # Initiate two points Q_a and Q_b at the generator point G
    Q_a, Q_b = G, G
    a, b = 0, 0 
    power_of_two = 1
    iterations = 0  # counter for iterations

    while iterations < max_iterations:  # while we haven't exceeded max_iterations
        # Walk until the power of two
        for _ in range(power_of_two):
            # Determine the step function depending on the value of Q_a[0] modulo 3
            i = Q_a[0] % 3
            if i == 0:
                # Step A: add G to Q_a and increment a
                Q_a = add_points(Q_a, G, a, p)
                a = (a + 1) % order
            elif i == 1:
                # Step B: double Q_a and double a
                Q_a = double_and_add(2, Q_a, a, p)
                a = (2 * a) % order
            else:
                # Step C: double Q_a, double a, add G to Q_a, and increment a
                Q_a = double_and_add(2, Q_a, a, p)
                a = (2 * a) % order
                Q_a = add_points(Q_a, G, a, p)
                a = (a + 1) % order

            # If Q_a is distinguished, return a and Q_a
            if is_distinguished(Q_a, t):
                return a, Q_a

            # Repeat the same steps for Q_b, but twice per iteration
            for _ in range(2):
                i = Q_b[0] % 3
                if i == 0:
                    Q_b = add_points(Q_b, G, a, p)
                    b = (b + 1) % order
                elif i == 1:
                    Q_b = double_and_add(2, Q_b, a, p)
                    b = (2 * b) % order
                else:
                    Q_b = double_and_add(2, Q_b, a, p)
                    b = (2 * b) % order
                    Q_b = add_points(Q_b, G, a, p)
                    b = (b + 1) % order

                # If Q_b is distinguished, return b and Q_b
                if is_distinguished(Q_b, t):
                    return b, Q_b

            iterations += 1  # increment the iteration counter

        # If Q_a and Q_b meet, double the walk length and continue
        if Q_a == Q_b:
            power_of_two *= 2
            Q_b = Q_a
            b = a

    # If we've reached this point, it means the algorithm has not found a collision
    # within the specified maximum number of iterations
    logging.info("No collision found within the specified maximum number of iterations.")
    return None