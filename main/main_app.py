# Python imports
import random

import numpy as np
import pandas as pd
from decimal import Decimal

# Info retrievers imports
from main.model.author import Author
from main.retrievers import ambiguity_score

# Model and loader_test imports
from main.loader import article_loader
from main.model.article_pair import ArticlePair

# Classifiers imports
from main.classifiers.knn import KNN
from main.classifiers.random_forest import RandomForest
from main.classifiers.cart import CART
from main.classifiers.svm import SVM
from main.classifiers.sequential import Sequential


def get_set(path):
    """Returns a matrix of data given the path to the CSV file. The heading row and NaN values are excluded."""
    df = pd.read_csv(path, sep=';', encoding='latin')
    return df.dropna(subset=['PMID1', 'PMID2', 'Authorship'], how='any').values


def compute_accuracy(classifier_results, labels):
    """Returns the accuracy (0-1) of a classifier given it's results and the actual labels."""
    correct = 0
    for i in range(len(labels)):
        if labels[i] == classifier_results[i]:
            correct += 1

    return Decimal(correct)/Decimal(len(labels))


def normalize_set(ds, binaries: list):
    """Applies standardization (AKA Z-Score normalization) on the 2 dimensional set.
    Binaries features are not normalized."""

    normalized_set = np.array(ds)
    numpy_set = np.array(ds)

    for i in range(len(numpy_set[0])):
        if not binaries[i]:
            avg = np.mean(numpy_set[:, i])
            std = np.std(numpy_set[:, i])

            normalized_set[:, i] = (numpy_set[:, i] - avg) / std

    return normalized_set


def fill_empty_with_average(set):
    """Given a set, replaces all the -1 values with the respective column average (-1 values excluded)"""
    matrix = np.array(set)
    averages = list()

    # Getting each row's average without considering -1 values.
    for col in range(len(matrix[0])):
        sum, count = 0, 0

        for row in range(len(matrix)):
            if matrix[row][col] == -1:
                pass
            else:
                sum = sum + matrix[row][col]
                count = count + 1

        averages.append(sum/count)

    # Applying the averages to the -1 values
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            if matrix[i][j] == -1:
                matrix[i][j] = averages[j]

    return matrix


def fill_empty_with_random(set):
    """Given a set, replaces all the -1 values with a random value between the respective column min and max"""
    matrix = np.array(set)
    mins_maxs = list()

    # Gettin each row's max and min value
    for col in range(len(matrix[0])):
        min_col_val = 2**30
        max_col_val = -1 * 2**30

        for row in range(len(matrix)):
            cell_value = matrix[row][col]

            if not cell_value == -1:
                if cell_value > max_col_val:
                    max_col_val = cell_value
                if cell_value < min_col_val:
                    min_col_val = cell_value
        mins_maxs.append([min_col_val, max_col_val])

    # Applying the random values in the min-max ranges
    for row in range(len(matrix)):
        for col in range(len(matrix[row])):
            min_col_val, max_col_val = mins_maxs[col][0], mins_maxs[col][1]

            if matrix[row][col] == -1:
                matrix[row][col] = random.uniform(min_col_val, max_col_val)

    return matrix


def get_confusion_matrix(predictions, labels):
    """Given a classifier predictions and the actual labels, returns a 2x2 (confusion) matrix:
        | True Negatives | False Positives |
        | False Negatives| True Positives  |"""

    tp, fp, tn, fn = 0, 0, 0, 0

    for i in range(len(predictions)):
        if predictions[i] == labels[i]:
            if predictions[i] == 1:
                tp = tp + 1
            else:
                tn = tn + 1
        else:
            if predictions[i] == 0:
                fn = fn + 1
            else:
                fp = fp + 1

    tp, fp, tn, fn = tp/len(predictions), fp/len(predictions), tn/len(predictions), fn/len(predictions)
    return np.array([[tn, fp], [fn, tp]])


def run_classifier(classifier, x_train, y_train, x_test, y_test):
    """Trains and tests the classifier. Finally prints the accuracy and the confusion matrix"""
    name = classifier.__class__.__name__

    classifier.fit(x_train, y_train)
    predictions = classifier.predict(x_test)

    accuracy = compute_accuracy(predictions, y_test)
    conf_matrix = get_confusion_matrix(predictions, y_test)

    print('\n'+name+" accuracy: "+str(int(accuracy*100))+'%')
    print(conf_matrix)


def test_classifiers(x_train_norm, y_train, x_test_norm, y_test):
    """Tests a bunch of classifiers. Prints accuracy and confusion matrix for each"""

    # Trying out different values for K (5,7 and 9) in K-NN and trees for the random forest (50, 70 and 90)
    for i in range(5, 11, 2):
        # KNN - CLASSIFIER
        classifier = KNN(i)
        run_classifier(classifier, x_train_norm, y_train, x_test_norm, y_test)
        print("For N = " + str(i))

        # RANDOM FOREST - CLASSIFIER
        classifier = RandomForest(i * 10)
        run_classifier(classifier, x_train_norm, y_train, x_test_norm, y_test)
        print("With " + str(i * 10) + " trees")

    # CART - CLASSIFIER
    classifier = CART()
    run_classifier(classifier, x_train_norm, y_train, x_test_norm, y_test)

    # SVM - CLASSIFIER
    classifier = SVM()
    run_classifier(classifier, x_train_norm, y_train, x_test_norm, y_test)


def cross_validate(data, target, k):
    """Performs a k-fold cross validation using the given classifier, data and target"""

    # Shuffling dataset
    data_target = list()

    for i in range(len(data)):
        row = list(data[i])
        row.append(target[i])

        data_target.append(row)

    data_target = np.array(data_target)
    np.random.shuffle(data_target)

    # Dividing dataset in partitions
    partitions = list()
    rows_per_partition = int(len(data_target) / k)

    for i in range(k):
        first_row = i * rows_per_partition
        last_row = first_row + rows_per_partition

        partitions.append(data_target[first_row:last_row][:])

    # Applying the cross-validation
    scores = list()

    for i in range(k):
        training = list()
        for partition in partitions:
            if not np.array_equal(partition, partitions[i]):
                for row in partition:
                    training.append(row)
        training = np.array(training)

        testing = partitions[i]

        x_train, y_train = training[:, :len(training[i]) - 2], training[:, len(training[i]) - 1]
        x_test, y_test = testing[:, :len(testing[i]) - 2], testing[:, len(testing[i]) - 1]

        classifier = RandomForest(50)
        classifier.fit(x_train, y_train)
        scores.append(compute_accuracy(classifier.predict(x_test), y_test))

    return np.array(scores)


def print_feature_importances(classifier):
    features_importances = classifier.feature_importances_()
    features_names = ArticlePair.feature_names()

    print("\nFeature Importances:")
    for i in range(len(features_names)):
        print(features_names[i]+str(features_importances[i]*100)+"%")


def main(training_set_path="./../dataset/1500_pairs_train.csv", testing_set_path="./../dataset/400_pairs_test.csv"):
    """Main method - Trains and tests various classifiers_test"""
    # Positive instances in the training set: 970. Negative instances in the training set: 503
    # Positive instances in the testing set: 217. Negative instances in the testing set: 182
    # Nominative training set length is 1500 Instances. After filtering out null values there are 1473 instances
    # Nominative testing set length is 400 Instances. After filtering out null values there are 397 instances

    # Retrieving sets
    training_set = get_set(training_set_path)
    testing_set = get_set(testing_set_path)

    x_train = list()
    training_labels = np.array(training_set[:, 8])

    x_test = list()
    testing_labels = np.array(testing_set[:, 8])

    y_train, y_test = list(), list()

    # Filling training set data
    for i in range(len(training_set)):
        pmid_left = int(training_set[i][0])
        pmid_right = int(training_set[i][4])

        # Loading first article and setting infos
        article1 = article_loader.load_article(pmid_left)

        author1 = Author(lastname=str(training_set[i][1]),
                         forename=str(training_set[i][3]),
                         initials=str(training_set[i][2]))

        article1.set_main_author(author1)
        article1.set_ambiguity(
            ambiguity_score.get_ambiguity_score(namespace_lastname=training_set[i][1],
                                                namespace_initial=training_set[i][2],
                                                dataset=training_set,
                                                ds_ln1_col=1, ds_fn1_col=2,
                                                ds_ln2_col=5, ds_fn2_col=6))
        # Loading second article and setting infos
        article2 = article_loader.load_article(pmid_right)

        author2 = Author(lastname=str(training_set[i][5]),
                         forename=str(training_set[i][7]),
                         initials=str(training_set[i][6]))

        article2.set_main_author(author2)
        article2.set_ambiguity(
            ambiguity_score.get_ambiguity_score(namespace_lastname=training_set[i][5],
                                                namespace_initial=training_set[i][6],
                                                dataset=training_set,
                                                ds_ln1_col=1, ds_fn1_col=2,
                                                ds_ln2_col=5, ds_fn2_col=6))
        # Creating the pair
        article_pair = ArticlePair(article1, article2)

        # Putting the pair's vector in the training set
        pair_scores = article_pair.scores()

        # print(article_pair.feature_names())
        # print(article_pair.binary_scores())
        print(pair_scores)
        article1.print_detail_info()
        article2.print_detail_info()

        x_train.append(pair_scores)
        if 'NO' in training_labels[i]:
            y_train.append(0)
        else:
            y_train.append(1)

    # Filling testing set data
    for i in range(len(testing_set)):
        pmid_left = int(testing_set[i][0])
        pmid_right = int(testing_set[i][4])

        # Loading first article and setting infos
        article1 = article_loader.load_article(pmid_left)

        author1 = Author(lastname=str(testing_set[i][1]),
                         forename=str(testing_set[i][3]),
                         initials=str(testing_set[i][2]))

        article1.set_main_author(author1)
        article1.set_ambiguity(
            ambiguity_score.get_ambiguity_score(testing_set[i][1],
                                                testing_set[i][2],
                                                testing_set,
                                                1, 2, 5, 6))

        # Loading second article and setting infos
        article2 = article_loader.load_article(pmid_right)

        author2 = Author(lastname=str(testing_set[i][5]),
                         forename=str(testing_set[i][7]),
                         initials=str(testing_set[i][6]))

        article2.set_main_author(author2)
        article2.set_ambiguity(
            ambiguity_score.get_ambiguity_score(testing_set[i][5],
                                                testing_set[i][6],
                                                testing_set,
                                                1, 2, 5, 6))

        # Creating the pair
        article_pair = ArticlePair(article1, article2)

        # Putting the pair's vector in the testing set
        x_test.append(article_pair.scores())
        if 'NO' in testing_labels[i]:
            y_test.append(0)
        else:
            y_test.append(1)

    y_train = np.array(y_train).astype('int')
    y_test = np.array(y_test).astype('int')

    # Filling empty datas (-1) with average values
    x_train_filled = fill_empty_with_average(x_train)  # ALTERNATIVE: fill_empty_with_random(x_train)
    x_test_filled = fill_empty_with_average(x_test)     # ALTERNATIVE: fill_empty_with_random(x_test)

    # Normalizing data
    binaries_features = ArticlePair.binary_scores()

    x_train_norm = normalize_set(x_train_filled, binaries_features).astype('float64')
    x_test_norm = normalize_set(x_test_filled, binaries_features).astype('float64')

    # Testing many classifiers (OPTIONAL)
    test_classifiers(x_train_norm, y_train, x_test_norm, y_test)

    # K-Cross validating the best classifier (Random Forest)
    k = 10
    data = np.concatenate((x_train_norm, x_test_norm), axis=0)
    target = np.concatenate((y_train, y_test), axis=0)
    scores = cross_validate(data, target, k)
    accuracy = scores.mean()

    print("\nRandom Forest accuracy with "+str(k)+"-fold cross validation: "
          + str(int(accuracy*100))+"%")

    # Running the main (best) classifier
    best_classifier = RandomForest(50)

    best_classifier.fit(x_train_norm, y_train)
    predictions = best_classifier.predict(x_test_norm)

    print("\nBest classifier accuracy: "+str(compute_accuracy(predictions, y_test)*100)+"%")

    # Printing each feature importance for the classifier
    print_feature_importances(best_classifier)


if __name__ == '__main__':
    main("./../dataset/1500_pairs_train.csv", "./../dataset/400_pairs_test.csv")
