#   This is the script for the second DI app.
#
#   Flask application to fetch the data and plot it using Bokeh
#
#   Adapted from:
#   https://github.com/bokeh/bokeh/blob/master/examples/embed/simple/simple.py
#
#   Seto Balian, Jul 17 2016
#

from flask import Flask, request, render_template, redirect
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from bokeh.charts import Bar
from bokeh.charts.attributes import CatAttr
import requests
import pandas as pd

def fetch_data(drugs):
    """Fetch the data.

    Get the relevant data using the openFDA API. https://open.fda.gov
    Note that you should use the generic drug name.

    Args:
        drugs: String list of generic drug names

    Returns:
        list of two-element lists: table with col1=drug name, col2 = proportion
        of reports containing drug marked as interacting.
        Only looks for fatal cases and those submitted by physicians.

    """

    # Clean up input
    drugs = drugs.split(',')
    drugs = [s.strip() for s in drugs]

    # API query URL
    # includes reported by physician: primarysource.qualification = 1
    # includes fatal report: seriousnessdeath = 1
    pre_url_terms = ["https://api.fda.gov/drug/event.json?search=",
                 "seriousnessdeath:\"1\"",
                 "+AND+primarysource.qualification:\"1\"",
                 "+AND+patient.drug.openfda.generic_name:"]
    pre_url = ''.join(pre_url_terms)

    # This means drug was reported as "interacting"
    interacting_url = "+AND+patient.drug.drugcharacterization:\"3\""

    # Very important to limit to 1 because we are interested in counting reports
    # and we can get this from the metadata of the openFDA search result
    post_url = "&limit=1"
    dquotes = "\""

    # Query API
    proportion = []
    for drug in drugs:

        drug_in_qoutes = dquotes + drug + dquotes

        # First, total number of reports
        url_request = pre_url + drug_in_qoutes + post_url
        json_data = requests.get(url_request).json()
        try:
            num_records = json_data["meta"]["results"]["total"]
        except KeyError:
            print("Warning: drug not found, setting records to 0.")
            num_records = 0

        if num_records == 0:
            proportion.append(0)
            continue
        # else

        # Now, suspected as interacting
        url_request = pre_url + drug_in_qoutes + interacting_url + post_url
        json_data = requests.get(url_request).json()
        try:
            interacting = json_data["meta"]["results"]["total"]
        except KeyError:
            interacting = 0

        proportion.append(float(interacting)/float(num_records))


    output = [[drug, proportion[i]] for i, drug in enumerate(drugs)]
    # Sort output
    output.sort(key=lambda x: x[1],reverse=True)
    return output

app = Flask(__name__)
app.vars = {}

@app.route('/')
def main():
    return redirect('/index')


@app.route('/index', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/plotbokeh', methods=['POST'])
def plotbokeh():
    """Embeddig of Bokeh plot. """

    # Get form input
    app.vars['drugs'] = request.form['drugs']

    drugs = str(app.vars['drugs'])

    # Get the data
    data = fetch_data(drugs)
    print("openFDA query success.")

    print("List of drugs: " + drugs)

    # Plot the data
    plot_data = {'Drug': [item[0] for item in data],
                 'R': [item[1] for item in data]}
    plot_data = pd.DataFrame(plot_data)

    fig = Bar(plot_data, values='R', width=800, height=800,
            title="Proportion of fatal reports marked \"interacting\"",
            color="green", label=CatAttr(columns=['Drug'], sort=False),
            legend='',
            xlabel="Drug",
            ylabel="Proportion of fatal reports")

    fig.axis.major_label_text_font_size = "14pt"
    fig.axis.axis_label_text_font_size = "14pt"
    fig.title.text_font_size="12pt"

    # Resources to include Bokeh figure
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    script, div = components(fig, INLINE)
    html = render_template(
        'plot.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources
    )
    return encode_utf8(html)

# Heroku port 33507
if __name__ == "__main__":
    app.run(port=33507)
