import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from bson.objectid import ObjectId

from u19_ncrcrg.tools import db

df = pd.DataFrame
job_records = df(list(db['Experiments'].find()))


def jobs_by_modality_graph():
    job_modality_counts = job_records.groupby(['modality']).size().reset_index(name="Number of Jobs")

    fig = px.pie(job_modality_counts, values='Number of Jobs', names='modality', title="Jobs by Modality")

    fig.update_layout(transition_duration=500)
    return fig


def jobs_over_time():
    job_counts = job_records.groupby(["_id"]).size().reset_index(name="Cumulative Jobs")

    month = []
    count = []
    for index, rec in job_counts.iterrows():
        created_time = str(ObjectId(rec["_id"]).generation_time)
        created_date = created_time.split(' ')
        created_month = str(created_date[0]).split('-')
        created_str = f'{created_month[1]}-{created_month[0]}'
        month.append(created_str)
        count.append(int(index) + 1)

    inter_df = pd.DataFrame({'Month': month, 'Count': count})

    job_counts = inter_df.groupby(["Month"], sort=False)["Count"].max().reset_index()

    fig = px.line(job_counts, x='Month', y="Count",
                  title='Jobs Processed over Time')

    return fig


def jobs_by_org():
    job_counts = job_records.groupby(["organization"]).size().reset_index(name="Total Jobs Processed")
    mod_jobs_count = job_counts.rename(columns={'organization': 'Organization'})

    fig = px.bar(mod_jobs_count, y='Organization', x="Total Jobs Processed", color="Organization",
                 title="Jobs by Organization", orientation='h', template="plotly_white", color_discrete_sequence=px.colors.qualitative.D3)

    fig.update_layout(showlegend=False)
    return fig


def jobs_by_org_stacked():
    job_counts = job_records.groupby(["organization"]).size().reset_index(name="Total Jobs Processed")
    mod_jobs_count = job_counts.rename(columns={'organization': 'Organization'})
    fig = go.Figure()
    for x in range(mod_jobs_count.shape[0]):
        fig.add_trace(go.Bar(
            y=["Source"],
            x=[mod_jobs_count.iloc[x]['Total Jobs Processed']],
            name=mod_jobs_count.iloc[x]['Organization'],
            orientation='h',
            marker=dict(
                color='rgba(246, 78, 139, 0.6)',
                line=dict(color='rgba(246, 78, 139, 1.0)', width=3)
            )
        ))

    fig.update_layout(barmode='stack')

    return fig


def jobs_by_tool():
    job_counts = job_records.groupby(["module"]).size().reset_index(name="Total Jobs Processed")

    fig = px.pie(job_counts, names='module', values="Total Jobs Processed", title="Jobs by Tool")

    return fig


def jobs_by_tool_stacked():
    job_counts = job_records.groupby(["module"]).size().reset_index(name="Total Jobs Processed")

    fig = px.pie(job_counts, names='module', values="Total Jobs Processed", title="Jobs by Tool")

    return fig