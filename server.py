"""SFparks."""

from flask import Flask, render_template, redirect, request, flash, session, jsonify
from flask_debugtoolbar import DebugToolbarExtension
from jinja2 import StrictUndefined
import json
from geojson import Feature, Point, FeatureCollection
from model import db, connect_to_db, User, Popos, Posm
from geofunctions import geocode_location, get_routing_times
from mappingfunctions import find_close_parks, add_routing_time, make_feature_coll


app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "ABCDEF"

# Raise an error for undefined variables in Jinja2
app.jinja_env.undefined = StrictUndefined


@app.route('/')
def index():
    """Homepage; render SF parks."""

    popos = Popos.query.all()
    posm = Posm.query.all()

    popos = make_feature_coll(popos)
    posm = make_feature_coll(posm)

    return render_template('homepage.html',
                            popos=popos,
                            posm=posm)


# @app.route('/current-location.json', methods=['POST'])
# def get_current_location:
    """Find user's current location based on browser data."""


# RETURN ALL OF HE MARKERS IN JSON
# MARKERS: KEY, VALUE: ALL MARKERS


@app.route('/query', methods=['GET'])
def query_parks():
    """Return results from users' query based on origin location, time profile, and routing profile."""
    
    origin = request.args.get('origin')
    time = request.args.get('time')
    routing = 'walking' # hardcoding for now
                        # TODO: incorporate routing into query params

    # user_id = session.get('user_id')

    # # if the user is logged in, show favorites
    # if user_id:
    #     favorites = Favorite.query.filter_by(user_id=user_id).all()


    # Geocode user input; origin is an instance of named tuple
    origin = geocode_location(origin)

    # Get all park objects in database
    parks = Popos.query.all()
    posm = Posm.query.all()

    # Create a dictionary containing park objects within the bounding radius heuristic
    close_parks = find_close_parks(origin, time, routing, parks)

    # Create a list of GeoJSON objects for close parks
    geojson_destinations = [park.create_geojson_object() for park in close_parks.values()]
        # [{'geometry': {'type': 'Point', 'coordinates': [-122.40487, 37.79277]}, 'type': 'Feature', 'properties': {'name': u'600 California St', 'address': u'600 California St'}}, {'geometry': {'type': 'Point', 'coordinates': [-122.40652, 37.78473]}, 'type': 'Feature', 'properties': {'name': u'Westfield Sky Terrace (Wesfield Center Mall)', 'address': u'845 Market St'}},

    # Convert origin coordinates to GeoJSON object
    geojson_origin = Feature(geometry=Point((origin.longitude, origin.latitude)))
        # Point(reverse_coord(geocoded_origin)) --> Feature(geometry=geojson_origin)

    # Create list of GeoJSON objects for get_routing_times argument
    routing_params = [geojson_origin] + geojson_destinations
        # TODO .insert to list
        # Can these be put in as two separate lists?
    
    routing_times = get_routing_times(routing_params, routing)
    # distance matrix (in seconds)

    # Create markers for the results of the user's query by adding each routing time to a park's GeoJSON properties
    markers = add_routing_time(geojson_destinations, routing_times)

    markers = json.dumps(FeatureCollection(markers))

    print type(markers)

    return render_template('query.html',
                            origin=origin,
                            time=time,
                            # close_parks=close_parks,
                            geojson_origin=geojson_origin,
                            geojson_destinations=geojson_destinations,
                            # routing_times=routing_times,
                            markers=markers)

    




#run server in interactive mode
# python -i server.py
# control C (just once)
# stops the script
# then can call functions

# @app.route('/favorites')
# # Add individual <user> to URL?
# # def show favorites:
#     """Display user's favorite parks."""

#     # user_id = session.get("user_id")
    
#     # if user_id:
#         # favorites = Favorite.query.filter_by(user_id=user_id).all()

#     # return render_template('favorites.html',
#     #                         favorites=favorites)


# @app.route('/add-to-favorites', methods=['POST'])
# def add_to_favorites():
#     """Add park to user's favorites and add to database."""

#     # user_id = session.get("user_id")
#     # get park_id
#     park_id = request.form.get('id') # update this field

    
#     # favorite = Favorite(park_id=park_id, user_id=user_id)

#     # see if user has favorited park before
#     Favorite.query.filter(Favorite.park_id == park_id)
    
#     #if...
#         # db.session.add(favorite)
#         # db.session.commit()

#     return jsonify(status='success', id= xx) #update this)


@app.route('/login', methods=['POST']) #note: took out 'GET' method
def login():
    """Show login form."""

    return render_template('login.html')


@app.route('/process-login', methods=['POST'])
def process_login():
    """Log in existing users and redirect to homepage."""

    email = request.form.get('email') # diff. from request.form('email')??
    password = request.form.get('password')

    # select the user from the database who has the given email (if any)
    user = User.query.filter(User.email==email).first()

    if user:
        # if user in database, check that password is correct
        if password == user.password:
            session['user'] = user.user_id
            
            flash("You're logged in.")
            return redirect('/')

        else:  # if password does not match database
            # flash message, stay on page
            
            flash('Your password is incorrect. Please enter your information again or register as a new user.')
            return redirect('/login')

    else:
        flash('Please register as a new user.')
        return redirect('register.html')


@app.route('/register', methods=['POST'])
def register():
    """Show registration form."""

    return render_template('register.html')


@app.route('/process-registration', methods=['POST'])
def process_registration():
    """Add new user to database and log them in."""

    email = request.form.get('email')
    password = request.form.get('password')

    # instantiate a user object with the information provided
    new_user = User(email=email, password=password)
    
    # add user to session and commit to database
    db.session.add(new_user)
    db.session.commit()

    # add user to the session; redirect to homepage
    session['user'] = new_user.user_id
    
    flash("You're logged in.")
    return redirect('/')


@app.route('/logout', methods=['POST'])
def logout():
    """Log user out."""

    # remove user id from session
    del session['user']
    
    flash('You are now logged out.')
    return redirect('/')


##############################################################################

if __name__ == "__main__":
    # Set debug=True to invoke the DebugToolbarExtension
    app.debug = True

    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run()