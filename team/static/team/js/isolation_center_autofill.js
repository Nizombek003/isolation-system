(function () {
    function toTravelMinutes(distanceKm) {
        if (!distanceKm || Number.isNaN(Number(distanceKm))) {
            return "";
        }
        return Math.max(5, Math.round(Number(distanceKm) * 4));
    }

    function applyAutofill(selectEl, mapData) {
        var selectedName = selectEl.value;
        if (!selectedName || !mapData[selectedName]) {
            return;
        }

        var item = mapData[selectedName];
        var addressInput = document.getElementById("id_address");
        var capacityInput = document.getElementById("id_capacity");
        var travelInput = document.getElementById("id_travel_time_minutes");
        var notesInput = document.getElementById("id_notes");

        if (addressInput) {
            addressInput.value = item.address || "";
        }

        if (capacityInput) {
            capacityInput.value = item.capacity_auto || "";
        }

        if (travelInput) {
            travelInput.value = toTravelMinutes(item.distance_km);
        }

        if (notesInput) {
            var note = "Registon maydoniga masofa: " + item.distance_km + " km";
            if (item.map_code) {
                note += " | Xarita kodi: " + item.map_code;
            }
            notesInput.value = note;
        }
    }

    function initIsolationCenterAutofill() {
        var nameSelect = document.getElementById("id_name");
        if (!nameSelect) {
            return;
        }

        var rawMap = nameSelect.getAttribute("data-hospital-map");
        if (!rawMap) {
            return;
        }

        var mapData = {};
        try {
            mapData = JSON.parse(rawMap);
        } catch (err) {
            return;
        }

        var sync = function () {
            applyAutofill(nameSelect, mapData);
        };

        nameSelect.addEventListener("change", sync);
        nameSelect.addEventListener("input", sync);

        // Some admin widgets may not emit normal change events consistently.
        var lastValue = nameSelect.value;
        setInterval(function () {
            if (nameSelect.value !== lastValue) {
                lastValue = nameSelect.value;
                sync();
            }
        }, 300);

        if (nameSelect.value) {
            applyAutofill(nameSelect, mapData);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initIsolationCenterAutofill);
    } else {
        initIsolationCenterAutofill();
    }
})();
