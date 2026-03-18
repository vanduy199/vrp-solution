import random


def create_individual(num_points):
    individual = list(range(1, num_points))
    random.shuffle(individual)
    return individual
    
def initialize_population(pop_size, num_points):
    population = []
    for _ in range(pop_size):
        individual = create_individual(num_points)
        population.append(individual)
    return population

def calculate_fitness(individual, distance_matrix):
    total_distance = 0
    current = 0
    for point in individual:
        total_distance += distance_matrix[current][point]
        current = point
    total_distance += distance_matrix[current][0]
    fitness = 1 / total_distance
    return fitness, total_distance

def selection(population, fitness_scores):
    tournament_size = 3
    selected = random.sample(list(zip(population, fitness_scores)), tournament_size)
    selected.sort(key=lambda x: x[1], reverse=True)
    return selected[0][0]

def crossover(parent1, parent2):
    size = len(parent1)
    start, end = sorted(random.sample(range(size), 2))
    child = [None] * size
    child[start:end] = parent1[start:end]
    pointer = 0
    for gene in parent2:
        if gene not in child:
            while child[pointer] is not None:
                pointer += 1
            child[pointer] = gene
    return child


def mutate(individual, mutation_rate=0.1):
    if random.random() < mutation_rate:
        i, j = random.sample(range(len(individual)), 2)
        individual[i], individual[j] = individual[j], individual[i]
    return individual


def genetic_algorithm(distance_matrix, population_size=50, generations=200):
    num_points = len(distance_matrix)
    population = initialize_population(population_size, num_points)
    best_solution = None
    best_distance = float("inf")
    for generation in range(generations):
        fitness_scores = []
        distances = []
        for individual in population:
            fitness, dist = calculate_fitness(individual, distance_matrix)
            fitness_scores.append(fitness)
            distances.append(dist)
            if dist < best_distance:
                best_distance = dist
                best_solution = individual
        new_population = []
        for _ in range(population_size):
            parent1 = selection(population, fitness_scores)
            parent2 = selection(population, fitness_scores)
            child = crossover(parent1, parent2)
            child = mutate(child)
            new_population.append(child)
        population = new_population
    return best_solution, best_distance