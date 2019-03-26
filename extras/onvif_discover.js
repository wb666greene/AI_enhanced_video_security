// onvif_discover.js  15SEP2018wbk
//
// Simple use of node-onvif library to scan subnet for onvif cameras and print key URLs needed to access them.
// Run once before starting the python AI code on a new netowrk or after a change of network cameras.
//
// Usage:
// nodejs onvif_discover.js
//
const onvif = require('node-onvif');
const fs = require('fs');


// delete old URL file
fs.unlink('cameraURL.txt', (err) => {
    if (err) console.log('No previous cameraURL.txt file.');
});

 
console.log('Start the discovery process.');
// Find the ONVIF network cameras.
// It will take about 3 seconds.
onvif.startProbe().then((device_list) => {
    console.log(device_list.length + ' devices were found.\n');
    // Show the device name and the URL of the end point.
    device_list.forEach((device) => {
        //console.log('- ' + device.urn);
        //console.log('  - ' + device.name);
        //console.log('  - ' + device.xaddrs[0] + '\n');  // what we really care about!

	    let odevice = new onvif.OnvifDevice({
		    xaddr: device.xaddrs[0],
            user : 'admin',     // this will fail if different cameras have different default credentials
            pass : 'admin'      // if no password is required, this doesn't seem to hurt anything.
	    });
        odevice.init().then((info) => {
            console.log('*** ' + device.xaddrs[0]);
            console.log(JSON.stringify(info, null, '  '));
            //console.log('Getting Current Profile.');
            let profile = odevice.getCurrentProfile()
            //console.log(JSON.stringify(profile, null, '  '));     // dump complete profile
            let stream = profile['stream']['rtsp'];     // grab rtsp URL
            console.log('Stream URL:  ' + JSON.stringify(stream, null, '  '));
            let snapshot = profile['snapshot'];     // grab snapshot URL
            console.log('Snapshot URL:  ' + JSON.stringify(snapshot, null, '  ')  + '\n');
            // Write a file of the snapshot URLs of the found cameras, for use by python AI code.
            try {
                //fs.appendFileSync('cameraURL.txt', JSON.stringify(snapshot, null, '  ') + '\n'); // put "" around snapshot URL text
                fs.appendFileSync('cameraURL.txt', snapshot + '\n');   // no "" around snapshot URL text
            } catch (err) {
                console.log('File write failed!');
                /* Handle the error */
            }        
            /* // This stuff was just playing around to learn a bit
            // Get a list of the profiles in the device
            console.log('Getting Profile List:');
            let profile_list = odevice.getProfileList();
            //for(let i=0; i<profile_list.length; i++) {    // print the list to see what is in it
            //    console.log(JSON.stringify(profile_list[i], null, '  '));
            //}

            // Sample code about uisng profiles, Find the profile whose video resolution is the smallest
            reso = profile['video']['encoder']['resolution'];
            console.log('Initial resolution: ' + reso['width'] + ' x ' + reso['height']); 
            let min_square = 8000 * 8000;
            let min_index = 0;
            for(let i=0; i<profile_list.length; i++) {
                let resolution = profile_list[i]['video']['encoder']['resolution'];
                let square = resolution['width'] * resolution['height'];
                if(square < min_square) {
                    min_square = square;
                    min_index = i;
                }
            }
            //console.log(JSON.stringify(profile_list[min_index], null, '  '));     // show found profile
            // Change the current profile to the one found, not clear how useful this is since it doesn't seem to persist
            profile = odevice.changeProfile(min_index);
            // Show the new video resolution
            reso = profile['video']['encoder']['resolution'];
            console.log('Changed to: ' + reso['width'] + ' x ' + reso['height'] + '\n\n');
            */
        }).catch((error) => {  // onvif.init()
            console.error(error);
        });
    }); // device.list
// I'm still a bit fuzzy here about the "promise" systax:  method().then((result) => { do something }).catch((error) => { handle error });
}).catch((error) => {   // startProbe()
    console.error(error);
});


