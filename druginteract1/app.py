#   This is the script for the first DI app.
#
#   Flask application to fetch the data and plot it using Bokeh
#
#   Adapted from:
#   https://github.com/bokeh/bokeh/blob/master/examples/embed/simple/simple.py
#
#   Seto Balian, Jul 15 2016
#

from flask import Flask, request, render_template, redirect
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from bokeh.charts import Bar
from bokeh.charts.attributes import CatAttr
import requests
import pandas as pd

def fetch_data(sample_drug, drugs_to_compare):
    """Fetch the data.

    Get the relevant data using the openFDA API. https://open.fda.gov
    Note that you should use the generic drug name.

    Args:
        sample_drug: String of generic drug name to investigate
        drugs_to_compare: String of generic drug names (separated by commas) to
            compare with the sample drug.

    Returns:
        table (list of two-element lists): the first element is the drug name
        in drugs_to_compare, the second element is the number of records
        reported by a physician that resulted in death having the entry in
        drugs_to_compare in addition to the sample drug. The output is sorted
        in decreasing number of records.

    """

    # Clean up input
    sample_drug = sample_drug.strip()
    drugs_to_compare = drugs_to_compare.split(',')
    drugs_to_compare = [s.strip() for s in drugs_to_compare]

    # API query URL
    # includes reported by physician: primarysource.qualification = 1
    # includes fatal report: seriousnessdeath = 1
    url_terms = ["https://api.fda.gov/drug/event.json?search=",
                 "seriousnessdeath:\"1\"",
                 "+AND+primarysource.qualification:\"1\"",
                 "+AND+patient.drug.openfda.generic_name:\"",
                 sample_drug,
                 "\"+AND+patient.drug.openfda.generic_name:\""]

    pre_compare = ''.join(url_terms)

    # Very important to limit to 1 because we are interested in counting reports
    # and we can get this from the metadata of the openFDA search result
    post_compare = "\"&limit=1"

    url_requests = [pre_compare
                    + drug + post_compare for drug in drugs_to_compare]

    # Query API getting total number of records matching the search
    num_records = []
    for url_request in url_requests:
        json_data = requests.get(url_request).json()
        try:
            rc = json_data["meta"]["results"]["total"]
        except KeyError:
            print("Warning: drug not found, setting records to 0.")
            rc = 0

        num_records.append(rc)

    # make output list: cols drug, num_records
    output = [[drug, num_records[i]] for i, drug in enumerate(drugs_to_compare)]

    # Sort output in decreasing num_records
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
    app.vars['sample_drug'] = request.form['sample_drug']
    app.vars['drugs_to_compare'] = request.form['drugs_to_compare']

    sample_drug = str(app.vars['sample_drug'])
    drugs_to_compare = str(app.vars['drugs_to_compare'])

    # Get the data
    data = fetch_data(sample_drug, drugs_to_compare)

    print("openFDA query success.")
    print("Sample drug: " + sample_drug)
    print("Drugs to compare: " + drugs_to_compare)

    # Plot the data
    plot_data = {'Drug': [item[0] for item in data],
                 'N': [item[1] for item in data]}
    plot_data = pd.DataFrame(plot_data)

    fig = Bar(plot_data, values='N', width=800, height=800,
            title="Number of fatal reports containing " + sample_drug
                  + " and drug on x-axis",
            color="navy", label=CatAttr(columns=['Drug'], sort=False),
            legend='',
            xlabel="Drug in same report as " + sample_drug,
            ylabel="Number of fatal reports")

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
