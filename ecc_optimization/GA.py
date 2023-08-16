import ai_ecc_utils
from datetime import datetime
from deap import base, creator, tools  # Framework for evolutionary algorithms
from Crypto.Util.number import getPrime  # Generate prime numbers
import logging  # Import the logging library
import random
import matplotlib.pyplot as plt
import os

POP_SIZE = 500  # Size of the population, i.e., the total number of individuals in each generation
CXPB = 0.5  # Crossover probability, i.e., the likelihood that two individuals will produce offspring different from themselves
MUTPB = 0.2  # Mutation probability, i.e., the likelihood that an individual will undergo a change
NGEN = 40  # Number of generations, i.e., the total number of times the genetic algorithm will cycle through the process of generating new individuals
MULTIPARENT_CXPB = 0.1 # Probability with which selected individuals will undergo multi-parent crossover, or mating.
ELITISM_RATE = 0.1 # Define the elitism rate

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
filename = os.path.join(log_dir, datetime.now().strftime("GA_log_%Y%m%d_%H%M%S.log"))
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename=filename,  # specify the file name
                    filemode='a')  # 'a' to append to existing file

def customMutation(individual, indpb, mutation_rate):
    # Initialize the degree of mutation. This represents the standard deviation of the Gaussian 
    # distribution from which the mutation amount will be drawn.
    degree_of_mutation = 5

    # Adjust degree of mutation based on mutation_rate
    if mutation_rate > 0.5:
        degree_of_mutation = 10  # Larger degree of mutation for higher mutation rates
    else:
        degree_of_mutation = 2  # Smaller degree of mutation for lower mutation rates

    # Generate a random float between 0 and 1. If it's less than the mutation rate, 
    # then proceed with the mutation. This means that mutation will occur with a probability 
    # equal to the mutation rate.
    if random.random() < mutation_rate:
        # Iterate over each parameter in the individual
        for i in range(len(individual)):
            # Generate another random float. If it's less than indpb, mutate this parameter.
            # indpb stands for "independent probability", and it's the chance of each attribute to 
            # be mutated.
            if random.random() < indpb:
                # If the parameter is the third one (index 2), it corresponds to the prime number p.
                # Generate a new prime number using the BITS_PRIME_SIZE as the length in bits.
                if i == 2:
                    individual[i] = ai_ecc_utils.get_prime_for_p()  # Generate a prime number p

                # If the parameter is a tuple, it's the generator point (G). Generate a new point 
                # using the current values of a, b and p.
                elif isinstance(individual[i], tuple):
                    individual[i] = ai_ecc_utils.find_generator_point(individual[0], individual[1], individual[2])
                # For the other parameters (a and b), add a perturbation drawn from a Gaussian 
                # distribution with mean 0 and standard deviation equal to the degree of mutation. 
                # The round function is used to ensure we're still dealing with integers.
                else:
                    # Perturb the parameter with a value from a Gaussian distribution
                    individual[i] += round(random.gauss(0, degree_of_mutation))
    # Return the potentially mutated individual as a single-item tuple, as required by DEAP.
    return individual,


# Initialize the population for the genetic algorithm
def initPopulation(pcls, ind_init):
    logging.info("Initialize the population for the genetic algorithm")
    return pcls(ind_init(ai_ecc_utils.generate_curve()) for _ in range(POP_SIZE))

# Create a FitnessMax class and an Individual class
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)

# Toolbox contains the evolutionary operators
toolbox = base.Toolbox()
# Register 'initPopulation' function as 'population' in the toolbox.
# It initializes the population for the genetic algorithm, 
# creating a list of individuals, each individual being created using 'creator.Individual'.
toolbox.register("population", initPopulation, list, creator.Individual)

# Register 'cxTwoPoint' function (from deap.tools) as 'mate' in the toolbox. 
# 'cxTwoPoint' is a two-point crossover function, which will be used for mating two individuals.
toolbox.register("mate", tools.cxTwoPoint)

# Register 'customMutation' function as 'mutate' in the toolbox, with a parameter indpb=0.05. 
# 'customMutation' is a custom mutation function, which will be used to apply mutations on individuals. 
# indpb=0.05 means that each attribute of the individual has a 5% chance to be mutated.
# Assuming mutation_rate is set to 0.2 (20% chance to perform mutation when mutate function is called)
toolbox.register("mutate", customMutation, indpb=0.05, mutation_rate=0.2)


# Register 'selTournament' function (from deap.tools) as 'select' in the toolbox, with a parameter tournsize=3. 
# 'selTournament' is a function for tournament selection, which will be used to select individuals for the next generation. 
# tournsize=3 means that for each individual to be selected, a tournament of 3 individuals is conducted and the best one is chosen.
toolbox.register("select", tools.selTournament, tournsize=3)

# Register a new selection method in your toolbox for elitism
toolbox.register("selBest", tools.selBest)



# The main function that executes the genetic algorithm
def main():

    logging.critical('Program started')

    pop = toolbox.population()  # Initialize the population

    fitnesses = map(ai_ecc_utils.evaluate, pop)  # Evaluate the fitness of the initial population
    for ind, fit in zip(pop, fitnesses):  # Loop over the individuals and their fitnesses
        ind.fitness.values = fit  # Set the fitness of the individual

    # Compute number of individuals to carry over to the next generation
    elitism_number = round(len(pop) * ELITISM_RATE)

    mutation_rate = MUTPB  # Initial mutation rate

    # Initialize lists to store the min, max, and average fitness values
    min_fits, max_fits, avg_fits = [], [], []

    for g in range(NGEN):  # Loop over the generations
    
        #Logging the commencement of a new generation in the genetic algorithm. 
        # Each generation refers to a complete round of the genetic operations 
        # (selection, crossover, mutation) over the entire population.
        generation = g + 1  # Add 1 to start the generation count from 1
        logging.info(f"Starting Generation: {generation}")

        # Elitism selection: select top individuals and clone them
        elites = map(toolbox.clone, toolbox.selBest(pop, elitism_number))

        # Select the next generation individuals
        offspring = toolbox.select(pop, len(pop) - elitism_number)
        # Clone the selected individuals
        offspring = list(map(toolbox.clone, offspring))

        # Apply crossover (mating) on the offspring
        for i in range(0, len(offspring) - 2, 3):  # Loop over trios of offspring
            if random.random() < MULTIPARENT_CXPB:  # Check if crossover is to be performed
                child1, child2, child3 = offspring[i], offspring[i + 1], offspring[i + 2]
                cut1 = random.randint(0, len(child1) - 1)  # Random cut point for the three-point crossover
                cut2 = random.randint(cut1, len(child1))  # Second cut point should be greater or equal to the first cut point
                child1[cut1:cut2], child2[cut1:cut2], child3[cut1:cut2] = child2[cut1:cut2], child3[cut1:cut2], child1[cut1:cut2]
                del child1.fitness.values, child2.fitness.values, child3.fitness.values

        for child1, child2 in zip(offspring[::2], offspring[1::2]):  # Loop over pairs of offspring
            if random.random() < CXPB:  # Check if crossover is to be performed
                toolbox.mate(child1, child2)  # Perform crossover
                del child1.fitness.values  # Delete the fitness values of the children
                del child2.fitness.values  # The children will be evaluated later

        # Apply mutation on the offspring
        for mutant in offspring:  # Loop over the offspring
            toolbox.mutate(mutant, indpb=0.05, mutation_rate=mutation_rate)  # Perform mutation and pass the mutation rate
            del mutant.fitness.values  # Delete the fitness values of the mutant

        # Evaluate the new individuals
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]  # Find the individuals whose fitness is not yet calculated
        fitnesses = map(ai_ecc_utils.evaluate, invalid_ind)  # Calculate their fitness
        for ind, fit in zip(invalid_ind, fitnesses):  # Loop over the individuals and their fitnesses
            ind.fitness.values = fit  # Set the fitness of the individual

        # Elitism: add elite individuals to the next generation
        offspring.extend(elites)

        pop[:] = offspring  # Replace the current population with the offspring

        # Log the statistics of the current population
        fits = [ind.fitness.values[0] for ind in pop]  # List of fitness values of the population
        length = len(pop)  # Size of the population
        mean = sum(fits) / length  # Mean fitness
        sum2 = sum(x * x for x in fits)  # Sum of squares of the fitnesses
        std = abs(sum2 / length - mean ** 2) ** 0.5  # Standard deviation of fitness


        # Store the fitness values for plotting
        min_fits.append(min(fits))
        max_fits.append(max(fits))
        avg_fits.append(mean)
     
        # Adjust mutation rate based on generation number
        if generation < NGEN / 2:
            mutation_rate = 0.4  # Higher mutation rate in the early stages
        else:
            mutation_rate = 0.1  # Lower mutation rate in the later stages


    # Plotting the fitness progression
    plt.plot(min_fits, label='Min Fitness')
    plt.plot(max_fits, label='Max Fitness')
    plt.plot(avg_fits, label='Average Fitness')
    plt.xlabel('Generation')
    plt.ylabel('Fitness')
    plt.title('Fitness Progression over Generations - GA')
    plt.legend()

    # Save the figure
    fitness_prog_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fitness_progression')
    os.makedirs(fitness_prog_dir, exist_ok=True)
    filename = os.path.join(fitness_prog_dir, datetime.now().strftime("GA_fitness_prog_%Y%m%d_%H%M%S.png"))
    plt.savefig(filename)
  
    plt.show()


    # Print the statistics
    logging.critical("  Min %s" % min(fits))
    logging.critical("  Max %s" % max(fits))
    logging.critical("  Avg %s" % mean)
    logging.critical("  Std %s" % std)

    print("  Min %s" % min(fits))
    print("  Max %s" % max(fits))
    print("  Avg %s" % mean)
    print("  Std %s" % std)

    # Select and print the best individual from the final population
    best_ind = tools.selBest(pop, 1)[0]  # Select the best individual
    logging.critical("Best individual is %s, %s" % (best_ind, best_ind.fitness.values))  # Print the best individual and its fitness
    print("Best individual is %s, %s" % (best_ind, best_ind.fitness.values))  # Print the best individual and its fitness
          
    # Write the best parameters to the "ga_ecc_params.txt" file
    params_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ecc_parameters')
    params_file_path = os.path.join(params_dir, "ga_ecc_params.txt")
    with open(params_file_path, "w") as f:
        f.write(f"p: {best_ind[2]}\n")
        f.write(f"a: {best_ind[0]}\n")
        f.write(f"b: {best_ind[1]}\n")
        f.write(f"G_x: {best_ind[3][0]}\n")
        f.write(f"G_y: {best_ind[3][1]}\n")
        f.write(f"n: {best_ind[4]}\n")
        f.write(f"h: {best_ind[5]}\n")

    logging.critical('Program finished')
# Execute the main function if the script is run as the main module
if __name__ == "__main__":
    main()
