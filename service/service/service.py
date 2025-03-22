import bus
import bus.dummy  # noqa


def main():
    driver = bus.get_bus_driver("dummy", "test_driver")
    print(f"{driver.name=}")
    print(f"{driver.send([])=}")
    print(f"{driver.receive()=}")


if __name__ == "__main__":
    main()
