import main

application = main.getFlaskApp()

if __name__ == "__main__":
    print "Starting."
    main.begin()
    print "Killed."