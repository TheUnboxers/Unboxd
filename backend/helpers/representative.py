import numpy as np


def find_representative_movie(movies: np.ndarray, weights: np.ndarray) -> int:
    """
    Find the most representative movie from a list of movies based on a weighted total dot 
    product. Assuming the feature vectors are normalized, this is equivalent to a weighted 
    total cosine similarity.
    Args:
        `movies`: Feature vectors of movies.
        `weights`: Weights corresponding to the user rating of each movie.
    Returns:
        The index of the most representative movie in the input list.
    """
    n = len(movies)
    max_total_dot_product = -1
    representative_index = -1

    # Iterate through each movie to calculate its weighted total dot product with all other movies
    for i in range(n):
        total_dot_product = 0
        for j in range(n):
            if i != j:
                dot_product = np.dot(movies[i], movies[j])
                weighted_dot_product = dot_product * weights[j]
                total_dot_product += weighted_dot_product 

        # Update the representative movie if the current one has a higher total similarity
        if total_dot_product > max_total_dot_product:
            max_total_dot_product = total_dot_product
            representative_index = i

    # Return the index of the most representative movie
    return representative_index

