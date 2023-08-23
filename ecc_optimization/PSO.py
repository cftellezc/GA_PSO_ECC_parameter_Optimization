import ai_ecc_utils
from datetime import datetime
import logging
import random
import numpy as np
from sklearn.model_selection import ParameterGrid
import matplotlib.pyplot as plt
import os

# Constants for the PSO algorithm
SWARM_SIZE = 500  # Number of particles in the swarm
MAX_ITERATIONS = 40  # Maximum number of iterations
C1 = 1.0  # Cognitive parameter (influence of particle's best known position)
C2 = 2.5  # Social parameter (influence of swarm's best known position)
MAX_ITERATIONS_WITHOUT_IMPROVEMENT = 20 # Maximum number of iterations without improvement


# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
filename = os.path.join(log_dir, datetime.now().strftime("PSO_log_%Y%m%d_%H%M%S.log"))
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename=filename,  # specify the file name
                    filemode='a')  # 'a' to append to existing file

# Function to update the velocity of a particle
def update_velocity(particle, velocity, best_particle, global_best_particle, iteration, max_iterations):
    # Initialize an empty list to store the new velocities
    new_velocity = []
    
    # Calculate the dynamic inertia weight. This is a strategy to balance the global and local exploration abilities of the particles.
    # The inertia weight is set to a maximum value of 0.9 at the start of the optimization process to promote global exploration,
    # and linearly decreases to a minimum value of 0.4 to promote local exploration as the process progresses.
    w_max = 0.9
    w_min = 0.4
    inertia_weight = w_max - (w_max - w_min) * (iteration / max_iterations)

    # Iterate over each dimension of the particle's position
    for i in range(len(particle)):
        # Get the current velocity for this dimension
        v = velocity[i]
        
        # Generate two random numbers between 0 and 1 for stochasticity
        r1 = random.random()
        r2 = random.random()

        # If we're updating the generator point G (which is a tuple of two values)
        if i == 3:  
            # Calculate the cognitive and social components of the velocity update
            # The cognitive component represents the particle's memory of its own best position
            # The social component represents the particle's knowledge of the best position found by any particle in the swarm
            cognitive = tuple(C1 * r1 * (b - a) for a, b in zip(best_particle[i][:2], particle[i][:2]))
            social = tuple(C2 * r2 * (g - a) for a, g in zip(global_best_particle[i][:2], particle[i][:2]))
            
            # If the current velocity is a tuple (meaning we're dealing with the generator point G)
            # then calculate the new velocity as the weighted sum of the old velocity, the cognitive component, and the social component
            # Otherwise, calculate the new velocity as the sum of the cognitive and social components
            if isinstance(v, tuple):
                new_v = tuple(inertia_weight * v_i + c_i + s_i for v_i, c_i, s_i in zip(v, cognitive, social))
            else:
                new_v = tuple(c_i + s_i for c_i, s_i in zip(cognitive, social))
        else:
            # If we're not updating the generator point G, then calculate the cognitive and social components of the velocity update
            # and the new velocity as before
            cognitive = C1 * r1 * (best_particle[i] - particle[i])
            social = C2 * r2 * (global_best_particle[i] - particle[i])
            new_v = inertia_weight * v + cognitive + social

        # If we're not updating the generator point G, then ensure the velocity is positive
        # This is because negative velocities don't make sense in this context
        if i != 3:
            new_v = abs(new_v)

        # Add the new velocity to the list of new velocities
        new_velocity.append(new_v)

    # Return the list of new velocities
    return new_velocity


# Function to update the position of a particle
def update_position(particle, velocity):
    # Initialize an empty list to store the new positions
    new_particle = []
    
    # Iterate over each dimension of the particle's position
    for i in range(len(particle)):
        # Get the current position and velocity for this dimension
        p = particle[i]
        v = velocity[i]

        # If we're updating the generator point G (which is a tuple of two values)
        if i == 3:  
            # Calculate the new position as the sum of the current position and velocity
            # Ensure it's a tuple of two values, as G is a point on the elliptic curve, represented as (x, y)
            # Also, ensure the position is positive and rounded to the nearest integer, as G's coordinates must be integers
            new_p = tuple(abs(int(round(p_i + v_i))) for p_i, v_i in zip(p[:2], v[:2]))
        else:
            # If we're not updating the generator point G, then calculate the new position as before
            # and ensure the position is positive and rounded to the nearest integer
            new_p = abs(int(round(p + v)))

        # Add the new position to the list of new positions
        new_particle.append(new_p)

    # After updating the prime number p, replace it with a new prime number
    # This is done to ensure that p remains prime after the update
    new_particle[2] = ai_ecc_utils.get_prime_for_p()

    # After updating the coefficients a and b, and the prime number p, find a new generator point G that lies on the curve
    # This is done to ensure that G remains a point on the curve after the update
    a, b, p = new_particle[:3]
    new_particle[3] = ai_ecc_utils.find_generator_point(a, b, p)

    # Return the list of new positions
    return new_particle

def main():

    # Initialize the swarm with a set of random particles
    # Each particle represents a candidate solution to the optimization problem
    swarm = []
    for _ in range(SWARM_SIZE):
        # Generate a random elliptic curve, which is represented as a particle in the swarm
        swarm.append(ai_ecc_utils.generate_curve())

    # Initialize the velocities of the particles
    # The velocity of a particle determines how much the particle's position changes in each iteration
    velocities = []
    for _ in range(SWARM_SIZE):
        # Generate a random velocity for each dimension of the particle's position
        velocities.append([random.uniform(0, 1) for _ in range(6)])

    # Initialize the best known positions and fitness values of the particles
    # The best known position of a particle is the position with the highest fitness value that the particle has encountered so far
    best_positions = swarm.copy()
    best_fitnesses = [ai_ecc_utils.evaluate(particle)[0] for particle in swarm]

    # Find the global best known position and fitness value
    # The global best known position is the position with the highest fitness value that any particle in the swarm has encountered so far
    global_best_index = np.argmax(best_fitnesses)
    global_best_position = best_positions[global_best_index]
    global_best_fitness = best_fitnesses[global_best_index]

    # Initialize the best global fitness from the previous iteration
    prev_best_fitness = -np.inf
 
    # Initialize the counter for the number of iterations without improvement
    no_improvement_counter = 0
 
    # Initialize lists to store the min, max, and average fitness values
    min_fitnesses = []  # To store min fitness for each iteration
    max_fitnesses = []  # To store max fitness for each iteration
    avg_fitnesses = []  # To store average fitness for each iteration

    # Main PSO loop
    # In each iteration, the positions and velocities of the particles are updated based on their best known positions,
    # the global best known position, and their current velocities. The dynamic inertia weight is also calculated in each iteration.
    for iteration in range(MAX_ITERATIONS):
        # Log the current iteration number
        logging.info(f"Iteration {iteration + 1}")
        
        # Iterate over each particle in the swarm
        for i in range(SWARM_SIZE):
            # Get the current position and velocity of the particle
            particle = swarm[i]
            velocity = velocities[i]

            # Update the velocity of the particle
            # The new velocity is calculated based on the particle's current velocity, its best known position,
            # the best known position of any particle in the swarm, and a dynamic inertia weight.
            # The dynamic inertia weight is used to balance the global and local exploration abilities of the particles,
            # promoting global exploration at the start of the optimization process and local exploration as the process progresses.
            new_velocity = update_velocity(particle, velocity, best_positions[i], global_best_position, iteration, MAX_ITERATIONS)
            
            # Update the position of the particle based on its new velocity
            new_particle = update_position(particle, new_velocity)

            # Update the swarm and best known positions with the new velocity and position
            swarm[i] = new_particle
            velocities[i] = new_velocity

            # Evaluate the fitness of the new position
            fitness = ai_ecc_utils.evaluate(new_particle)[0]

            # If the fitness of the new position is better than the particle's best known fitness, update the particle's best known position and fitness
            if fitness > best_fitnesses[i]:
                best_positions[i] = new_particle
                best_fitnesses[i] = fitness

            # If the fitness of the new position is better than the global best known fitness, update the global best known position and fitness
            if fitness > global_best_fitness:
                global_best_position = new_particle
                global_best_fitness = fitness

        fitnesses = [ai_ecc_utils.evaluate(particle)[0] for particle in swarm]
        min_fitness = min(fitnesses)
        max_fitness = max(fitnesses)
        avg_fitness = sum(fitnesses) / len(fitnesses)

        min_fitnesses.append(min_fitness)  # Append to the list
        max_fitnesses.append(max_fitness)  # Append to the list
        avg_fitnesses.append(avg_fitness)  # Append to the list


        # If the global best fitness has not improved
        if global_best_fitness <= prev_best_fitness:
            # Increment the counter for the number of iterations without improvement
            no_improvement_counter += 1
        else:
            # If the global best fitness has improved, reset the counter
            no_improvement_counter = 0

        # If the number of iterations without improvement has reached the maximum, stop the algorithm
        if no_improvement_counter >= MAX_ITERATIONS_WITHOUT_IMPROVEMENT:
            print("No improvement in global best fitness for {} iterations. Stopping early.".format(MAX_ITERATIONS_WITHOUT_IMPROVEMENT))
            break

        # Update the best global fitness from the previous iteration
        prev_best_fitness = global_best_fitness

    # Plotting the min, max, and average fitness
    plt.plot(min_fitnesses, label="Min Fitness")
    plt.plot(max_fitnesses, label="Max Fitness")
    plt.plot(avg_fitnesses, label="Avg Fitness")
    plt.xlabel("Iteration")
    plt.ylabel("Fitness")
    plt.title("Fitness Progression over Iterations - PSO")
    plt.legend()

    # Save the figure
    fitness_prog_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fitness_progression')
    os.makedirs(fitness_prog_dir, exist_ok=True)
    filename = os.path.join(fitness_prog_dir, datetime.now().strftime("PSO_fitness_prog_%Y%m%d_%H%M%S.png"))
    plt.savefig(filename)

    plt.show()


    std_fitness = np.std(fitnesses)

    logging.critical("Min fitness: %s" % min_fitness)
    logging.critical("Max fitness: %s" % max_fitness)
    logging.critical("Avg fitness: %s" % avg_fitness)
    logging.critical("Std fitness: %s" % std_fitness)

    print("Min fitness: %s" % min_fitness)
    print("Max fitness: %s" % max_fitness)
    print("Avg fitness: %s" % avg_fitness)
    print("Std fitness: %s" % std_fitness)

    # Select and print the best particle from the final swarm
    # The best particle is the one with the highest fitness value
    best_particle_index = np.argmax(fitnesses)
    best_particle = swarm[best_particle_index]
    best_particle_fitness = fitnesses[best_particle_index]

    logging.critical("Best particle is %s, %s" % (best_particle, best_particle_fitness))
    print("Best particle is %s, %s" % (best_particle, best_particle_fitness))

    # Write the best parameters to the "pso_ecc_params.txt" file
    params_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ecc_parameters')
    params_file_path = os.path.join(params_dir, "pso_ecc_params.txt")
    with open(params_file_path, "w") as f:
        f.write(f"p: {best_particle[2]}\n")
        f.write(f"a: {best_particle[0]}\n")
        f.write(f"b: {best_particle[1]}\n")
        f.write(f"G_x: {best_particle[3][0]}\n")
        f.write(f"G_y: {best_particle[3][1]}\n")
        f.write(f"n: {best_particle[4]}\n")
        f.write(f"h: {best_particle[5]}\n")

    logging.critical('Program finished')


if __name__ == '__main__':
    # Run the main function if the script is being run directly
    main()
