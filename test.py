import multiprocessing



if __name__ == "__main__":
    manager = multiprocessing.Manager()

    dict_ = manager.dict()
    dict_[1] = 1

    print(dict_[1])