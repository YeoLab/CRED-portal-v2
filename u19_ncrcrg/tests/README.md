
<h1>Selenium Automation/Pytest Integration Setup Requirements</h1>
<p>See selenium documentation here: https://www.selenium.dev/documentation/</p>
<h2>Quick Start</h2>
<ul><li>Download and install chromedriver https://chromedriver.storage.googleapis.com/index.html
</li>
<li>pip install selenium</li>
<li>pip install pytest</li>
<li>Create test script</li>
<li>All test modules need to begin with the words test_ (i.e.def test_login)</li>
</ul>

<p>To run pytests via automation type the following on the command line <b> pytest -v  
(full path to test script file and filename) --username=username --password=password 
--driver_path /usr/local/bin/chromedriver</b> </p>

<ul>
<li>-v indicates verbose for detailed test output from pytest on the command line
<li>username and password can be any account in dev but depends on a cellranger directory in the users /raw_files directory to run job submission test
<li>--driver_path assumes default installation path location for chromedriver, otherwise change the input param to match the your location
</ul>

<h2>Other topics to understand and review</h2>
<ul>
<li>WebDriver Object</li>
<li>Selectors</li>
<li>Waits</li>

</ul>