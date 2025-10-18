USE FlightBooking;

-- ============================================================
-- Airlines
-- ============================================================
INSERT INTO Airlines (airline_name, iata_code) VALUES
('IndiGo', '6E'),
('Air India', 'AI'),
('SpiceJet', 'SG'),
('Vistara', 'UK'),
('Akasa Air', 'QP');

-- ============================================================
-- Flights
-- ============================================================
INSERT INTO Flights (airline_id, flight_number, source, destination, departure_time, arrival_time, base_fare) VALUES
(1,'6E201','Chennai','Kolkata','2025-10-15 08:00','2025-10-15 11:00',5500),
(1,'6E305','Bangalore','Ahmedabad','2025-10-15 14:30','2025-10-15 16:30',4800),
(2,'AI102','Delhi','Goa','2025-10-16 09:00','2025-10-16 11:10',6000),
(3,'SG505','Hyderabad','Pune','2025-10-16 13:00','2025-10-16 14:10',4100),
(4,'UK701','Lucknow','Jaipur','2025-10-17 10:00','2025-10-17 12:10',5200),
(5,'QP312','Ahmedabad','Kochi','2025-10-18 07:15','2025-10-18 09:00',4500),
(2,'AI220','Mumbai','Chandigarh','2025-10-18 17:00','2025-10-18 18:30',4700),
(3,'SG909','Kolkata','Bhubaneswar','2025-10-19 06:30','2025-10-19 09:10',5100),
(1,'6E404','Delhi','Bangalore','2025-10-20 08:00','2025-10-20 11:00',5600),
(2,'AI330','Mumbai','Hyderabad','2025-10-20 14:00','2025-10-20 16:00',4800),
(3,'SG707','Bangalore','Lucknow','2025-10-21 09:00','2025-10-21 11:30',5500),
(4,'UK802','Pune','Kolkata','2025-10-21 13:00','2025-10-21 15:30',5300),
(5,'QP418','Goa','Ahmedabad','2025-10-22 07:30','2025-10-22 09:15',4600),
(1,'6E509','Chennai','Jaipur','2025-10-22 11:00','2025-10-22 12:15',4700),
(2,'AI605','Delhi','Bhubaneswar','2025-10-23 06:30','2025-10-23 08:50',6000);

-- ============================================================
-- Passengers
-- ============================================================
INSERT INTO Passengers (full_name, email, phone) VALUES
('Isabel Conklin', 'belly.conklin@gmail.com', '9876543210'),
('Conrad Fisher', 'conrad.fisher@gmail.com', '9876543211'),
('Jeremiah Fisher', 'jeremiah.fisher@gmail.com', '9876543212'),
('Taylor Jewel', 'taylor.jewel@gmail.com', '9876543213'),
('Susannah Fisher', 'susannah.fisher@gmail.com', '9876543214'),
('Laurel Conklin', 'laurel.conklin@gmail.com', '9876543215'),
('Cam Fisher', 'cam.fisher@gmail.com', '9876543216'),
('Shawn', 'shawn@gmail.com', '9876543217'),
('Lila', 'lila@gmail.com', '9876543218'),
('Harper', 'harper@gmail.com', '9876543219');

-- ============================================================
-- Seats (Flight 1)
-- ============================================================
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked) VALUES
-- Business
(1,'1A','Business',0),(1,'1B','Business',0),(1,'1C','Business',0),(1,'1D','Business',0),(1,'1E','Business',0),
(1,'2A','Business',0),(1,'2B','Business',0),(1,'2C','Business',0),(1,'2D','Business',0),(1,'2E','Business',0),
-- Economy
(1,'3A','Economy',0),(1,'3B','Economy',0),(1,'3C','Economy',0),(1,'3D','Economy',0),(1,'3E','Economy',0),
(1,'4A','Economy',0),(1,'4B','Economy',0),(1,'4C','Economy',0),(1,'4D','Economy',0),(1,'4E','Economy',0),
(1,'5A','Economy',0),(1,'5B','Economy',0),(1,'5C','Economy',0),(1,'5D','Economy',0),(1,'5E','Economy',0);

-- Duplicate Seats for flights 2-15
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 2, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 3, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 4, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 5, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 6, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 7, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 8, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 9, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 10, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 11, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 12, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 13, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 14, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
INSERT INTO Seats (flight_id, seat_number, seat_class, is_booked)
SELECT 15, seat_number, seat_class, 0 FROM Seats WHERE flight_id=1;
