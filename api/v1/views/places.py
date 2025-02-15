#!/usr/bin/python3
"""
Route for handling Place objects and operations
"""
from flask import jsonify, abort, request
from api.v1.views import app_views, storage
from models.place import Place
from models.city import City
from models.state import State
from models.amenity import Amenity


def get_object_or_404(cls, obj_id):
    """
    Retrieves an object from storage or aborts with 404 if not found
    :param cls: Class of the object
    :param obj_id: ID of the object
    :return: The object if found, otherwise aborts with 404
    """
    obj = storage.get(cls, obj_id)
    if obj is None:
        abort(404, description=f"{cls.__name__} not found")
    return obj


@app_views.route("/cities/<city_id>/places", methods=["GET"], strict_slashes=False)
def places_by_city(city_id):
    """
    Retrieves all Place objects by city
    :param city_id: ID of the city
    :return: JSON of all Places in the city
    """
    city_obj = get_object_or_404(City, city_id)
    place_list = [place.to_json() for place in city_obj.places]
    return jsonify(place_list)


@app_views.route("/cities/<city_id>/places", methods=["POST"], strict_slashes=False)
def place_create(city_id):
    """
    Creates a new Place object
    :param city_id: ID of the city
    :return: Newly created Place object
    """
    city_obj = get_object_or_404(City, city_id)

    place_json = request.get_json(silent=True)
    if place_json is None:
        abort(400, description="Not a JSON")

    if "user_id" not in place_json:
        abort(400, description="Missing user_id")

    user_obj = get_object_or_404("User", place_json["user_id"])

    if "name" not in place_json:
        abort(400, description="Missing name")

    place_json["city_id"] = city_id
    new_place = Place(**place_json)
    new_place.save()

    return jsonify(new_place.to_json()), 201


@app_views.route("/places/<place_id>", methods=["GET"], strict_slashes=False)
def place_by_id(place_id):
    """
    Retrieves a specific Place object by ID
    :param place_id: ID of the Place object
    :return: Place object with the specified ID
    """
    place_obj = get_object_or_404(Place, place_id)
    return jsonify(place_obj.to_json())


@app_views.route("/places/<place_id>", methods=["PUT"], strict_slashes=False)
def place_put(place_id):
    """
    Updates a specific Place object by ID
    :param place_id: ID of the Place object
    :return: Updated Place object
    """
    place_obj = get_object_or_404(Place, place_id)

    place_json = request.get_json(silent=True)
    if place_json is None:
        abort(400, description="Not a JSON")

    for key, value in place_json.items():
        if key not in ["id", "created_at", "updated_at", "user_id", "city_id"]:
            setattr(place_obj, key, value)

    place_obj.save()
    return jsonify(place_obj.to_json())


@app_views.route("/places/<place_id>", methods=["DELETE"], strict_slashes=False)
def place_delete_by_id(place_id):
    """
    Deletes a Place object by ID
    :param place_id: ID of the Place object
    :return: Empty dictionary with status code 200
    """
    place_obj = get_object_or_404(Place, place_id)
    storage.delete(place_obj)
    storage.save()
    return jsonify({})


@app_views.route("/places_search", methods=["POST"], strict_slashes=False)
def places_search():
    """
    Searches for Place objects based on JSON criteria
    :return: JSON list of Place objects matching the criteria
    """
    if not request.is_json:
        abort(400, description="Not a JSON")

    data = request.get_json()

    states = data.get("states", [])
    cities = data.get("cities", [])
    amenities = data.get("amenities", [])

    place_ids = set()

    # Include places from specified states
    if states:
        for state_id in states:
            state = storage.get(State, state_id)
            if state:
                for city in state.cities:
                    place_ids.update([place.id for place in city.places])

    # Include places from specified cities
    if cities:
        for city_id in cities:
            city = storage.get(City, city_id)
            if city:
                place_ids.update([place.id for place in city.places])

    # If no states or cities are specified, include all places
    if not states and not cities:
        place_ids.update([place.id for place in storage.all(Place).values()])

    # Filter places by amenities
    places = [storage.get(Place, place_id) for place_id in place_ids]
    if amenities:
        filtered_places = []
        for place in places:
            if place and all(amenity_id in [a.id for a in place.amenities] for amenity_id in amenities):
                filtered_places.append(place)
        places = filtered_places

    # Remove None values (if any)
    places = [place for place in places if place]

    return jsonify([place.to_json() for place in places])
