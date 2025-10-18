-- Disable foreign key checks for safe drops
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS Bookings;
DROP TABLE IF EXISTS Seats;
DROP TABLE IF EXISTS Flights;
DROP TABLE IF EXISTS Passengers;
DROP TABLE IF EXISTS Airlines;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- TABLE: Airlines
-- ============================================================
CREATE TABLE Airlines (
    airline_id INT AUTO_INCREMENT PRIMARY KEY,
    airline_name VARCHAR(255),
    iata_code VARCHAR(2) UNIQUE CHECK(CHAR_LENGTH(iata_code) = 2)
);

-- ============================================================
-- TABLE: Flights
-- ============================================================
CREATE TABLE Flights (
    flight_id INT AUTO_INCREMENT PRIMARY KEY,
    airline_id INT NOT NULL,
    flight_number VARCHAR(6) UNIQUE NOT NULL,
    source VARCHAR(50),
    destination VARCHAR(50),
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    base_fare DECIMAL(10,2) NOT NULL CHECK(base_fare > 0),
    FOREIGN KEY (airline_id) REFERENCES Airlines(airline_id),
    CHECK (source <> destination)
);

-- ============================================================
-- TABLE: Seats
-- ============================================================
CREATE TABLE Seats (
    seat_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_id INT NOT NULL,
    seat_number VARCHAR(10) NOT NULL,
    seat_class VARCHAR(20) CHECK(seat_class IN ('Economy','Business')) DEFAULT 'Economy',
    is_booked TINYINT(1) DEFAULT 0 CHECK(is_booked IN (0,1)),
    FOREIGN KEY (flight_id) REFERENCES Flights(flight_id),
    UNIQUE (flight_id, seat_number)
);

-- ============================================================
-- TABLE: Passengers
-- ============================================================
CREATE TABLE Passengers (
    passenger_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(50) NOT NULL UNIQUE,
    phone VARCHAR(13) CHECK(CHAR_LENGTH(phone) = 10)
);

-- ============================================================
-- TABLE: Bookings
-- ============================================================
CREATE TABLE Bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    passenger_id INT NOT NULL,
    flight_id INT NOT NULL,
    seat_id INT NOT NULL UNIQUE,
    pnr VARCHAR(12) NULL UNIQUE,       -- backend-generated
    booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    amount_paid DECIMAL(10,4) NOT NULL CHECK(amount_paid > 0),
    status VARCHAR(20) DEFAULT 'Confirmed',
    FOREIGN KEY (passenger_id) REFERENCES Passengers(passenger_id),
    FOREIGN KEY (flight_id) REFERENCES Flights(flight_id),
    FOREIGN KEY (seat_id) REFERENCES Seats(seat_id)
);
