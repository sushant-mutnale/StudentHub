import React, { useState, useEffect } from 'react';
import { scorecardService } from '../services/scorecardService';
import { FaStar } from 'react-icons/fa';

const ScorecardForm = ({ applicationId, candidateId, onClose }) => {
               const [templates, setTemplates] = useState([]);
               const [selectedTemplate, setSelectedTemplate] = useState(null);
               const [scores, setScores] = useState({});
               const [decision, setDecision] = useState("hold"); // pass, hold, reject
               const [feedback, setFeedback] = useState("");
               const [submitting, setSubmitting] = useState(false);

               useEffect(() => {
                              loadTemplates();
               }, []);

               const loadTemplates = async () => {
                              try {
                                             const data = await scorecardService.getTemplates();
                                             setTemplates(data);
                                             if (data.length > 0) setSelectedTemplate(data[0]);
                              } catch (error) {
                                             console.error("Failed to load templates", error);
                              }
               };

               const handleScoreChange = (criteriaName, value) => {
                              setScores(prev => ({ ...prev, [criteriaName]: parseInt(value) }));
               };

               const handleSubmit = async (e) => {
                              e.preventDefault();
                              setSubmitting(true);

                              const criteriaScores = Object.entries(scores).map(([name, score]) => ({
                                             name,
                                             score,
                                             weight: selectedTemplate.criteria.find(c => c.name === name)?.weight || 1
                              }));

                              const payload = {
                                             template_id: selectedTemplate.id,
                                             application_id: applicationId,
                                             decision,
                                             feedback,
                                             scores: criteriaScores
                              };

                              try {
                                             await scorecardService.submitScorecard(payload);
                                             onClose(); // Close modal on success
                                             alert("Scorecard submitted successfully!");
                              } catch (error) {
                                             console.error("Failed to submit scorecard", error);
                                             alert("Failed to submit scorecard.");
                              } finally {
                                             setSubmitting(false);
                              }
               };

               if (!selectedTemplate) return <div>Loading...</div>;

               return (
                              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                                             <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                                                            <div className="p-6 border-b flex justify-between items-center sticky top-0 bg-white">
                                                                           <h2 className="text-xl font-bold text-gray-800">Submit Evaluation</h2>
                                                                           <button onClick={onClose} className="text-gray-500 hover:text-gray-700">&times;</button>
                                                            </div>

                                                            <div className="p-6">
                                                                           {/* Template Selector */}
                                                                           <div className="mb-6">
                                                                                          <label className="block text-sm font-medium text-gray-700 mb-2">Evaluation Type</label>
                                                                                          <select
                                                                                                         className="w-full border rounded-md p-2"
                                                                                                         value={selectedTemplate.id}
                                                                                                         onChange={(e) => {
                                                                                                                        const t = templates.find(t => t.id === e.target.value);
                                                                                                                        setSelectedTemplate(t);
                                                                                                                        setScores({}); // Reset scores on template change
                                                                                                         }}
                                                                                          >
                                                                                                         {templates.map(t => (
                                                                                                                        <option key={t.id} value={t.id}>{t.name}</option>
                                                                                                         ))}
                                                                                          </select>
                                                                           </div>

                                                                           {/* Scoring Criteria */}
                                                                           <form onSubmit={handleSubmit}>
                                                                                          <div className="space-y-6 mb-8">
                                                                                                         {selectedTemplate.criteria.map((criteria) => (
                                                                                                                        <div key={criteria.name} className="border-b pb-4 last:border-0">
                                                                                                                                       <div className="flex justify-between mb-2">
                                                                                                                                                      <label className="font-medium text-gray-800">{criteria.name}</label>
                                                                                                                                                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                                                                                                                                                                     Weight: {criteria.weight}x
                                                                                                                                                      </span>
                                                                                                                                       </div>
                                                                                                                                       <p className="text-sm text-gray-500 mb-3">{criteria.description}</p>

                                                                                                                                       <div className="flex gap-4">
                                                                                                                                                      {[1, 2, 3, 4, 5].map((rating) => (
                                                                                                                                                                     <label key={rating} className="flex flex-col items-center cursor-pointer">
                                                                                                                                                                                    <input
                                                                                                                                                                                                   type="radio"
                                                                                                                                                                                                   name={criteria.name}
                                                                                                                                                                                                   value={rating}
                                                                                                                                                                                                   checked={scores[criteria.name] === rating}
                                                                                                                                                                                                   onChange={(e) => handleScoreChange(criteria.name, e.target.value)}
                                                                                                                                                                                                   className="sr-only"
                                                                                                                                                                                                   required
                                                                                                                                                                                    />
                                                                                                                                                                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center border transition-colors ${scores[criteria.name] === rating
                                                                                                                                                                                                                  ? 'bg-blue-600 text-white border-blue-600'
                                                                                                                                                                                                                  : 'bg-white text-gray-400 border-gray-200 hover:border-blue-400'
                                                                                                                                                                                                   }`}>
                                                                                                                                                                                                   {rating}
                                                                                                                                                                                    </div>
                                                                                                                                                                                    <span className="text-xs text-gray-400 mt-1">{
                                                                                                                                                                                                   rating === 1 ? 'Poor' : rating === 5 ? 'Excel' : ''
                                                                                                                                                                                    }</span>
                                                                                                                                                                     </label>
                                                                                                                                                      ))}
                                                                                                                                       </div>
                                                                                                                        </div>
                                                                                                         ))}
                                                                                          </div>

                                                                                          {/* Overall Feedback */}
                                                                                          <div className="mb-6">
                                                                                                         <label className="block text-sm font-medium text-gray-700 mb-2">Feedback & Notes</label>
                                                                                                         <textarea
                                                                                                                        className="w-full border rounded-md p-3 h-32 focus:ring-2 focus:ring-blue-500"
                                                                                                                        placeholder="Write your detailed evaluation here..."
                                                                                                                        value={feedback}
                                                                                                                        onChange={(e) => setFeedback(e.target.value)}
                                                                                                                        required
                                                                                                         ></textarea>
                                                                                          </div>

                                                                                          {/* Decision */}
                                                                                          <div className="mb-8">
                                                                                                         <label className="block text-sm font-medium text-gray-700 mb-2">Final Decision</label>
                                                                                                         <div className="flex gap-4">
                                                                                                                        {['pass', 'hold', 'reject'].map((d) => (
                                                                                                                                       <label key={d} className={`flex-1 p-3 rounded-lg border-2 cursor-pointer text-center capitalize font-semibold transition-all ${decision === d
                                                                                                                                                                     ? d === 'pass' ? 'border-green-500 bg-green-50 text-green-700'
                                                                                                                                                                                    : d === 'reject' ? 'border-red-500 bg-red-50 text-red-700'
                                                                                                                                                                                                   : 'border-yellow-500 bg-yellow-50 text-yellow-700'
                                                                                                                                                                     : 'border-gray-200 hover:border-gray-300'
                                                                                                                                                      }`}>
                                                                                                                                                      <input
                                                                                                                                                                     type="radio"
                                                                                                                                                                     name="decision"
                                                                                                                                                                     value={d}
                                                                                                                                                                     checked={decision === d}
                                                                                                                                                                     onChange={(e) => setDecision(e.target.value)}
                                                                                                                                                                     className="sr-only"
                                                                                                                                                      />
                                                                                                                                                      {d}
                                                                                                                                       </label>
                                                                                                                        ))}
                                                                                                         </div>
                                                                                          </div>

                                                                                          <div className="flex justify-end gap-3 pt-4 border-t">
                                                                                                         <button
                                                                                                                        type="button"
                                                                                                                        onClick={onClose}
                                                                                                                        className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
                                                                                                         >
                                                                                                                        Cancel
                                                                                                         </button>
                                                                                                         <button
                                                                                                                        type="submit"
                                                                                                                        disabled={submitting}
                                                                                                                        className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                                                                                                         >
                                                                                                                        {submitting ? 'Submitting...' : 'Submit Evaluation'}
                                                                                                         </button>
                                                                                          </div>
                                                                           </form>
                                                            </div>
                                             </div>
                              </div>
               );
};

export default ScorecardForm;
