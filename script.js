const API_BASE = "http://127.0.0.1:8000";

// DOM Elements
const searchForm = document.getElementById("search-form");
const flightsList = document.getElementById("flights-list");
const bookingSection = document.getElementById("booking-section");
const bookingDetails = document.getElementById("booking-details");
const bookingForm = document.getElementById("booking-form");
const confirmationSection = document.getElementById("confirmation-section");
const confirmationDetails = document.getElementById("confirmation-details");
const mybookingsForm = document.getElementById("mybookings-form");
const mybookingsList = document.getElementById("mybookings-list");

function scrollToSection(id){
    document.getElementById(id).scrollIntoView({behavior:"smooth"});
    history.replaceState(null, null, " ");
}
let selectedFlight = null;



// ------------------ Display Flights ------------------
function displayFlights(flights) {
    if (!flights.length) {
        flightsList.innerHTML = "<p>No flights found</p>";
        return;
    }
    flightsList.innerHTML = "";
    flights.forEach(f => {
        const card = document.createElement("div");
        card.className = "flight-card";
        card.innerHTML = `
            <div class="flight-info">
                <p><strong>${f.airline}</strong> | Flight: ${f.flight_number}</p>
                <p>${f.origin} → ${f.destination}</p>
                <p>Departure: ${new Date(f.departure_time).toLocaleString()}</p>
                <p>Price: $${f.dynamic_price}</p>
                <p>Seats available: ${f.seats_available}</p>
            </div>
            <button class="book-btn">Book</button>
        `;
        card.querySelector(".book-btn").addEventListener("click", () => selectFlight(f));
        flightsList.appendChild(card);
    });
}

// ------------------ Fetch All Flights on Page Load ------------------
async function fetchAllFlights() {
    flightsList.innerHTML = "<p>Loading flights...</p>";
    try {
        const res = await fetch(`${API_BASE}/flights`);
        const flights = await res.json();
        displayFlights(flights);
    } catch (err) {
        flightsList.innerHTML = "<p>Error loading flights</p>";
        console.error(err);
    }
}

// ------------------ Flight Search ------------------
searchForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    flightsList.innerHTML = "<p>Loading flights...</p>";

    const from = document.getElementById("from").value;
    const to = document.getElementById("to").value;
    const date = document.getElementById("date").value;

    let url = `${API_BASE}/flights?from=${from}&to=${to}`;
    if (date) url += `&date=${date}`;

    try {
        const res = await fetch(url);
        const flights = await res.json();
        displayFlights(flights);
    } catch (err) {
        flightsList.innerHTML = "<p>Error fetching flights</p>";
        console.error(err);
    }
});

// ------------------ Booking ------------------
function selectFlight(flight) {
    selectedFlight = flight;
    bookingSection.classList.remove("hidden");
    bookingDetails.innerHTML = `
        <p><strong>${flight.airline}</strong> | Flight: ${flight.flight_number}</p>
        <p>${flight.origin} → ${flight.destination}</p>
        <p>Departure: ${new Date(flight.departure_time).toLocaleString()}</p>
        <p>Price: $${flight.dynamic_price}</p>
        <p>Seats available: ${flight.seats_available}</p>
    `;
    confirmationSection.classList.add("hidden");
}

bookingForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const passengerId = document.getElementById("passenger-id").value;
    const seatNumber = document.getElementById("seat-number").value || null;

    if (!selectedFlight) return;

    try {
        const res = await fetch(`${API_BASE}/bookings`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                flight_id: selectedFlight.flight_id,
                seat_number: seatNumber,
                passenger_id: parseInt(passengerId)
            })
        });
        const booking = await res.json();

        const payRes = await fetch(`${API_BASE}/bookings/pay/${booking.booking_id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ passenger_id: parseInt(passengerId) })
        });
        const confirmed = await payRes.json();
        displayConfirmation(confirmed);

    } catch (err) {
        alert("Booking/payment failed. Check console.");
        console.error(err);
    }
});

function displayConfirmation(booking) {
    bookingSection.classList.add("hidden");
    confirmationSection.classList.remove("hidden");
    confirmationDetails.innerHTML = `
        <p>Booking ID: ${booking.booking_id}</p>
        <p>PNR: ${booking.pnr}</p>
        <p>Flight: ${booking.flight_number}</p>
        <p>Passenger: ${booking.passenger_name}</p>
        <p>Seat: ${booking.seat_number}</p>
        <p>Amount Paid: $${booking.amount_paid}</p>
        <p>Status: ${booking.status}</p>
    `;
}

// ------------------ My Bookings ------------------
mybookingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const passengerId = document.getElementById("my-passenger-id").value;
    mybookingsList.innerHTML = "<p>Loading bookings...</p>";

    try {
        const res = await fetch(`${API_BASE}/bookings/passenger/${passengerId}`);
        const bookings = await res.json();
        displayMyBookings(bookings);
    } catch (err) {
        mybookingsList.innerHTML = "<p>Error fetching bookings</p>";
        console.error(err);
    }
});

function displayMyBookings(bookings) {
    if (!bookings.length) {
        mybookingsList.innerHTML = "<p>No bookings found</p>";
        return;
    }
    mybookingsList.innerHTML = "";
    bookings.forEach(b => {
        const card = document.createElement("div");
        card.className = "booking-card";
        card.innerHTML = `
            <div class="booking-info">
                <p>Booking ID: ${b.booking_id}</p>
                <p>PNR: ${b.pnr}</p>
                <p>Flight: ${b.flight_number}</p>
                <p>Seat: ${b.seat_number}</p>
                <p>Status: ${b.status}</p>
            </div>
            <button class="cancel-btn">Cancel</button>
        `;
        card.querySelector(".cancel-btn").addEventListener("click", () => cancelBooking(b.booking_id));
        mybookingsList.appendChild(card);
    });
}

async function cancelBooking(bookingId) {
    if (!confirm("Are you sure you want to cancel this booking?")) return;
    try {
        await fetch(`${API_BASE}/bookings/cancel/${bookingId}`, { method: "POST" });
        alert("Booking cancelled successfully");
        mybookingsForm.dispatchEvent(new Event("submit")); // Refresh list
    } catch (err) {
        alert("Cancellation failed");
        console.error(err);
    }
}

// ------------------ Call fetchAllFlights on page load ------------------
window.addEventListener("DOMContentLoaded", fetchAllFlights);
